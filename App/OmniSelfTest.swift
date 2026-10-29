import Foundation

enum OmniSelfTest {
    static func run(local: String) async -> String {
        var report = "OmniForge /self-test\n[iPhone workspace] " + local
        if Bundle.main.bundleIdentifier == nil {
            report += "\n[iPhone bundle] FAIL: Missing bundle ID"
        } else {
            report += "\n[iPhone bundle] PASS: " + (Bundle.main.bundleIdentifier ?? "")
        }
        guard UserDefaults.standard.bool(forKey: "onlineEnabled"),
              let endpoint = UserDefaults.standard.string(forKey: "onlineEndpoint"),
              let url = URL(string: endpoint), url.scheme == "https", url.host != nil else {
            return report + "\n[Windows] SKIP: Remote HTTPS endpoint not enabled"
        }
        do {
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.timeoutInterval = 30
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            if let key = OnlineModelClient.readKey(), !key.isEmpty {
                req.setValue("Bearer " + key, forHTTPHeaderField: "Authorization")
            }
            let payload: [String:Any] = ["model":UserDefaults.standard.string(forKey:"onlineModel") ?? "qwen3:8b",
                                        "messages":[["role":"user","content":"/self-test"]]]
            req.httpBody = try JSONSerialization.data(withJSONObject: payload)
            let (data,response) = try await URLSession.shared.data(for: req)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                return report + "\n[Windows] FAIL: Remote host returned an HTTP error"
            }
            let object = try JSONSerialization.jsonObject(with:data) as? [String:Any]
            let choices = object?["choices"] as? [[String:Any]]
            let message = choices?.first?["message"] as? [String:Any]
            guard let result = message?["content"] as? String, !result.isEmpty else {
                return report + "\n[Windows] FAIL: Invalid remote diagnostic response"
            }
            report += "\n[Windows] " + result
            if url.path.hasSuffix("/v1/chat/completions") {
                var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
                components?.path = "/v1/remote/capabilities"
                components?.query = nil
                components?.fragment = nil
                if let capabilityURL = components?.url {
                    do {
                        var request = URLRequest(url: capabilityURL)
                        request.timeoutInterval = 15
                        if let key = OnlineModelClient.readKey(), !key.isEmpty {
                            request.setValue("Bearer " + key, forHTTPHeaderField: "Authorization")
                        }
                        let (data, response) = try await URLSession.shared.data(for: request)
                        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                            report += "\n[Remote access] FAIL: Capability endpoint unavailable"
                            return report
                        }
                        let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                        let desktop = object?["desktop"] as? [String: Any] ?? [:]
                        let network = object?["network"] as? [String: Any] ?? [:]
                        func yesNo(_ value: Any?) -> String { (value as? Bool) == true ? "YES" : "NO" }
                        report += "\n[Remote access] Tailscale detected: " + yesNo(network["tailscale_installed"])
                        report += "\n[Remote access] RustDesk on PATH: " + yesNo(desktop["rustdesk_on_path"])
                        report += "\n[Remote access] iPhone controls Windows verified: " + yesNo(desktop["iphone_can_control_windows_verified"])
                    } catch {
                        report += "\n[Remote access] FAIL: " + error.localizedDescription
                    }
                }
            }
        } catch {
            report += "\n[Windows] FAIL: " + error.localizedDescription
        }
        return report
    }
}
