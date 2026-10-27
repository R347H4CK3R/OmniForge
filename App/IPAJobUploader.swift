import SwiftUI
import Security

@MainActor final class IPAJobUploader: ObservableObject {
    @Published var repo = ""
    @Published var token = ""
    @Published var message = "Select a private GitHub repository"
    @Published var working = false

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
            message = "Submitted successfully. Check GitHub Actions in your private repository."
        } catch { message = error.localizedDescription }
    }
    private func error(_ text: String) -> NSError {
        NSError(domain:"OmniForge.Upload",code:1,userInfo:[NSLocalizedDescriptionKey:text])
    }
}
