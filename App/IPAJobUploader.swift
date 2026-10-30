import SwiftUI
import Security
import ZIPFoundation

@MainActor final class IPAJobUploader: ObservableObject {
    static let shared = IPAJobUploader()
    @Published var repo = UserDefaults.standard.string(forKey: "ipaJobRepository") ?? "" { didSet { UserDefaults.standard.set(repo, forKey: "ipaJobRepository") } }
    @Published var token = IPAJobUploader.readSavedToken() { didSet { IPAJobUploader.saveToken(token) } }
    private static let keychainService = "com.r347h4ck3r.omniforge.github-workbench"
    private static func saveToken(_ value: String) {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                                     kSecAttrService as String: keychainService,
                                     kSecAttrAccount as String: "private-workbench"]
        SecItemDelete(query as CFDictionary)
        if !value.isEmpty {
            var add = query
            add[kSecValueData as String] = Data(value.utf8)
            add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            SecItemAdd(add as CFDictionary, nil)
        }
    }
    private static func readSavedToken() -> String {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                                     kSecAttrService as String: keychainService,
                                     kSecAttrAccount as String: "private-workbench",
                                     kSecReturnData as String: true,
                                     kSecMatchLimit as String: kSecMatchLimitOne]
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return "" }
        return String(data: data, encoding: .utf8) ?? ""
    }

    @Published var message = "Select a private GitHub repository"
    @Published var working = false
    @Published var verifying = false
    @Published var lastRunURL = ""
    @Published var analysisTag = UserDefaults.standard.string(forKey: "ipaAnalysisTag") ?? "" {
        didSet { UserDefaults.standard.set(analysisTag, forKey: "ipaAnalysisTag") }
    }
    @Published var lastResult = "No tracked analysis yet"
    @Published var savedReports = ""
    private var latestArtifactID: Int?

    func submit(_ file: URL) async {
        guard !working else { return }
        working = true
        defer { working = false }
        do {
            let parts = repo.split(separator: "/")
            guard parts.count == 2, parts.allSatisfy({ $0.range(of: "^[A-Za-z0-9_.-]+$", options: .regularExpression) != nil }) else { throw error("Enter owner/repository") }
            guard file.pathExtension.lowercased() == "ipa" else { throw error("Choose an IPA") }
            let size = (try file.resourceValues(forKeys: [.fileSizeKey])).fileSize ?? 0
            guard size > 1024 && size < 1_900_000_000 else { throw error("IPA must be under 1.9 GB") }
            guard !token.isEmpty else { throw error("Enter a fine-grained GitHub token") }
            let name = parts.joined(separator: "/")
            let base = "https://api.github.com/repos/" + name
            func makeRequest(_ url: String, method: String, json: Data? = nil) -> URLRequest {
                var r = URLRequest(url: URL(string: url)!)
                r.httpMethod = method
                r.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
                r.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
                r.setValue("2022-11-28", forHTTPHeaderField: "X-GitHub-Api-Version")
                if let json { r.httpBody = json; r.setValue("application/json", forHTTPHeaderField: "Content-Type") }
                return r
            }
            func fetch(_ req: URLRequest) async throws -> Data {
                let (data, response) = try await URLSession.shared.data(for: req)
                guard let code = (response as? HTTPURLResponse)?.statusCode, (200...299).contains(code) else {
                    throw error("GitHub returned HTTP " + String((response as? HTTPURLResponse)?.statusCode ?? 0))
                }
                return data
            }
            message = "Checking repository privacy"
            let details = try JSONSerialization.jsonObject(with: await fetch(makeRequest(base, method: "GET"))) as? [String: Any]
            guard details?["private"] as? Bool == true else { throw error("Use a private repository to avoid publishing proprietary IPA contents") }
            let branch = details?["default_branch"] as? String ?? "main"
            let tag = "analysis-" + UUID().uuidString.lowercased()
            analysisTag = tag
            let releaseBody = try JSONSerialization.data(withJSONObject: ["tag_name":tag,"target_commitish":branch,"name":tag,"draft":true])
            message = "Creating private release"
            let created = try await fetch(makeRequest(base + "/releases", method: "POST", json: releaseBody))
            let release = try JSONSerialization.jsonObject(with: created) as? [String: Any]
            guard let raw = release?["upload_url"] as? String, let prefix = raw.split(separator: "{").first else { throw error("Release upload URL missing") }
            var url = URLComponents(string: String(prefix))!
            url.queryItems = [URLQueryItem(name: "name", value: "input.ipa")]
            guard let destination = url.url, destination.host == "uploads.github.com" else { throw error("Invalid upload destination") }
            message = "Uploading IPA to GitHub"
            var upload = makeRequest(destination.absoluteString, method: "POST")
            upload.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
            upload.timeoutInterval = 1800
            let (answer, response) = try await URLSession.shared.upload(for: upload, fromFile: file)
            guard (response as? HTTPURLResponse)?.statusCode == 201 else {
                throw error("Upload failed: " + String(decoding: answer.prefix(200), as: UTF8.self))
            }
            message = "Starting analysis"
            let payload = try JSONSerialization.data(withJSONObject: ["ref": branch,"inputs":["release_tag":tag,"ipa_asset":"input.ipa"]])
            _ = try await fetch(makeRequest(base + "/actions/workflows/ipa-workbench.yml/dispatches", method: "POST", json: payload))
            message = "Submitted; locate run in GitHub Actions"
            lastRunURL = "https://github.com/" + name + "/actions/workflows/ipa-workbench.yml"
        } catch { message = error.localizedDescription }
    }
    func checkLatestRun() async {
        guard !repo.isEmpty, !token.isEmpty,
              let url = URL(string: "https://api.github.com/repos/" + repo + "/actions/workflows/ipa-workbench.yml/runs?event=workflow_dispatch&per_page=10") else {
            lastResult = "BLOCKED: Configure your private repository and GitHub token."; return
        }
        var req = URLRequest(url: url)
        req.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        req.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        do {
            let (data, response) = try await URLSession.shared.data(for: req)
            guard (response as? HTTPURLResponse)?.statusCode == 200,
                  let object = try JSONSerialization.jsonObject(with: data) as? [String:Any],
                  let runs = object["workflow_runs"] as? [[String:Any]],
                  let latest = runs.first(where: { run in
                      guard !analysisTag.isEmpty else { return false }
                      return (run["display_title"] as? String) == "IPA Workbench — " + analysisTag
                  }), let id = latest["id"] as? Int else {
                lastResult = "Cannot establish that a workflow run belongs to this IPA submission. No result attributed."; return
            }
            lastRunURL = "https://github.com/" + repo + "/actions/runs/" + String(id)
            guard (latest["display_title"] as? String) == "IPA Workbench — " + analysisTag else {
                lastResult = "BLOCKED: Run identity mismatch; results not attributed."
                return
            }
            let status = latest["status"] as? String ?? "unknown"
            let conclusion = latest["conclusion"] as? String ?? "in progress"
            lastResult = "Latest private Workbench: " + status + " / " + conclusion + ". " + lastRunURL
            if status == "completed" && conclusion == "success" {
                var artifactsReq = URLRequest(url: URL(string: "https://api.github.com/repos/" + repo + "/actions/runs/" + String(id) + "/artifacts")!)
                artifactsReq.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
                artifactsReq.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
                let (artifactData, artifactResponse) = try await URLSession.shared.data(for: artifactsReq)
                if (artifactResponse as? HTTPURLResponse)?.statusCode == 200,
                   let listing = try JSONSerialization.jsonObject(with: artifactData) as? [String: Any],
                   let artifacts = listing["artifacts"] as? [[String: Any]],
                   let report = artifacts.first(where: { ($0["name"] as? String) == "IPA-workbench-results" }),
                   let artifactID = report["id"] as? Int {
                    latestArtifactID = artifactID
                    lastResult += "\\nReports artifact: https://github.com/" + repo +
                        "/actions/runs/" + String(id) + "/artifacts/" + String(artifactID) +
                        "\\nCompilation checks passed; no installed-app runtime verification."
                } else {
                    lastResult += "\\nNo verified downloadable results artifact found."
                }
            }
        } catch { lastResult = "Run status lookup failed: " + error.localizedDescription }
    }

    /// A foreground-only end-to-end submission and verification session.
    /// Never claims success until the correlated workflow and its artifact exist.
    func runFullVerification(_ ipa: URL) async {
        guard !verifying else { return }
        verifying = true
        defer { verifying = false }
        await submit(ipa)
        guard message.hasPrefix("Submitted;") || message.hasPrefix("Submitted to") else {
            lastResult = "Submission failed: " + message
            return
        }
        for attempt in 0..<45 {
            if Task.isCancelled {
                lastResult = "Verification cancelled."
                return
            }
            await checkLatestRun()
            if lastResult.contains("completed / success") {
                await downloadResults()
                if savedReports.hasPrefix("Saved ") {
                    lastResult += "\nReports retrieved; examine verification.json. Executable behavior and installation remain unverified."
                }
                return
            }
            if lastResult.contains("completed / failure") || lastResult.contains("completed / cancelled") {
                lastResult += "\nWorkbench failed; review its job logs before changing source."
                return
            }
            if attempt < 44 {
                try? await Task.sleep(for: .seconds(15))
            }
        }
        lastResult = "Run not verified within foreground session. Resume with /check-ipa-workbench."
    }

    func downloadResults() async {
        guard let artifactID = latestArtifactID, !repo.isEmpty, !token.isEmpty else {
            savedReports = "BLOCKED: Check a successful workflow with reports before downloading."; return
        }
        let url = URL(string: "https://api.github.com/repos/" + repo + "/actions/artifacts/" + String(artifactID) + "/zip")!
        var request = URLRequest(url: url)
        request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        do {
            let (temp, response) = try await URLSession.shared.download(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else {
                savedReports = "ERROR: Artifact download failed."; return
            }
            let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            let output = documents.appendingPathComponent("RemoteInvestigations", isDirectory: true)
                .appendingPathComponent(String(artifactID), isDirectory: true)
            try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
            guard let archive = Archive(url: temp, accessMode: .read) else {
                savedReports = "ERROR: Downloaded artifact is not a ZIP."; return
            }
            var count = 0
            var total: Int64 = 0
            for entry in archive {
                count += 1
                total += Int64(entry.uncompressedSize)
                guard count <= 5000, total <= 500_000_000 else {
                    throw NSError(domain:"OmniForge.Reports",code:1,userInfo:[NSLocalizedDescriptionKey:"Report archive exceeds extraction limits"])
                }
                let path = entry.path
                guard !path.hasPrefix("/"), !path.contains("\\"), !path.split(separator:"/").contains("..") else {
                    throw NSError(domain:"OmniForge.Reports",code:2,userInfo:[NSLocalizedDescriptionKey:"Unsafe report path"])
                }
                guard entry.type == .file || entry.type == .directory else { continue }
                let destination = output.appendingPathComponent(path).standardizedFileURL
                guard destination.path.hasPrefix(output.path + "/") else { continue }
                if entry.type == .directory {
                    try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
                } else {
                    try FileManager.default.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
                    _ = try archive.extract(entry, to: destination)
                }
            }
            let verificationFile = output.appendingPathComponent("verification.json")
            if FileManager.default.fileExists(atPath: verificationFile.path),
               let data = try? Data(contentsOf: verificationFile),
               let report = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let checks = report["checks"] as? [String: String] {
                let failures = checks.filter { $0.value != "PASS" }.map { $0.key }.sorted()
                let passed = checks.filter { $0.value == "PASS" }.count
                savedReports = "Saved \\(count) entries to " + output.path +
                    ". Verified checks: \\(passed)/\\(checks.count)." +
                    (failures.isEmpty ? " All declared checks passed." : " Failed: " + failures.joined(separator: ", ")) +
                    " App functional equivalence and installation remain unverified."
            } else {
                savedReports = "Saved \\(count) entries to " + output.path +
                    ". BLOCKED: verification.json missing or invalid; do not treat this analysis as verified."
            }
        } catch { savedReports = "ERROR: " + error.localizedDescription }
    }

    private func error(_ text: String) -> NSError {
        NSError(domain:"OmniForge.Upload",code:1,userInfo:[NSLocalizedDescriptionKey:text])
    }
}
