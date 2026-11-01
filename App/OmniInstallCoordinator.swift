import Foundation
import Combine

/// Shared approval gate for the on-device AI and the installer UI.
/// Only allowlisted packages can be requested; the AI cannot supply shell commands.
@MainActor final class OmniInstallCoordinator: ObservableObject {
    static let shared = OmniInstallCoordinator()
    static let packages: Set<String> = ["github-cli", "git", "python", "7zip"]
    @Published private(set) var pendingPackage: String?
    @Published private(set) var lastResult = "Not checked"
    private var continuation: CheckedContinuation<Bool, Never>?
    private(set) var sessionToken = ""

    func setSessionToken(_ value: String) { sessionToken = value }

    func requestApproval(for package: String) async -> Bool {
        guard Self.packages.contains(package), pendingPackage == nil else { return false }
        return await withCheckedContinuation { continuation in
            self.continuation = continuation
            self.pendingPackage = package
        }
    }

    func decide(_ accepted: Bool) {
        pendingPackage = nil
        let awaiting = continuation
        continuation = nil
        awaiting?.resume(returning: accepted)
    }

    func operation(_ operation: String, package: String) async -> String {
        guard Self.packages.contains(package), ["install", "status"].contains(operation) else {
            return "ERROR: Unsupported dependency or operation."
        }
        guard let address = UserDefaults.standard.string(forKey: "installerBridgeURL"),
              let base = URL(string: address), base.scheme == "https",
              base.host != nil, base.user == nil, base.password == nil,
              !sessionToken.isEmpty else {
            return "BLOCKED: Configure the trusted HTTPS bridge and session token in Install."
        }
        do {
            let url = base.appendingPathComponent(operation).appending(queryItems: [URLQueryItem(name: "package", value: package)])
            var request = URLRequest(url: url)
            request.httpMethod = operation == "install" ? "POST" : "GET"
            request.timeoutInterval = 120
            request.setValue("Bearer " + sessionToken, forHTTPHeaderField: "Authorization")
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, data.count < 128_000,
                  let payload = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                return "ERROR: Invalid installer bridge response."
            }
            let verified = payload["verified"] as? Bool == true || (operation == "status" && payload["installed"] as? Bool == true)
            let message = "HTTP \(http.statusCode), package=\(package), installed=\(payload["installed"] ?? false), verified=\(verified)"
            lastResult = message
            if (200...299).contains(http.statusCode) { return message }
            return "ERROR: " + message + " " + String(describing: payload["error"] ?? "")
        } catch {
            return "ERROR: Installer connection: " + error.localizedDescription
        }
    }

    func installWithApproval(_ package: String) async -> String {
        let status = await operation("status", package: package)
        if status.contains("installed=true") { return status }
        if status.hasPrefix("ERROR:") || status.hasPrefix("BLOCKED:") { return status }
        guard await requestApproval(for: package) else {
            return "BLOCKED: Installer permission declined or another request pending."
        }
        let installed = await operation("install", package: package)
        guard installed.contains("verified=true") else { return installed }
        return await operation("status", package: package)
    }
}
