import SwiftUI
import Foundation

/// Curated dependency installation through an explicitly trusted HTTPS bridge.
/// No arbitrary model-generated shell commands are accepted.
struct OmniInstallerView: View {
    @AppStorage("installerBridgeURL") private var endpoint = ""
    @State private var token = ""
    @State private var selected = "github-cli"
    @State private var status = "Not connected"
    @State private var busy = false
    @State private var approve = false
    private let packages = [
        ("GitHub CLI", "github-cli"),
        ("Git", "git"),
        ("Python 3", "python"),
        ("7-Zip", "7zip")
    ]
    var body: some View {
        NavigationStack {
            Form {
                Section("Trusted Windows bridge") {
                    TextField("https://private-host.example/installer", text: $endpoint)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                        .keyboardType(.URL)
                    SecureField("Session authorization token", text: $token)
                    Text("Configure your own HTTPS bridge to the Windows installer service. Do not expose its local HTTP port to the internet.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                Section("Dependencies") {
                    Picker("Package", selection: $selected) {
                        ForEach(packages, id: \.1) { item in Text(item.0).tag(item.1) }
                    }
                    Button("Check installation") { Task { await request(method: "GET", operation: "status") } }
                        .disabled(busy)
                    Button("Install and verify") { approve = true }
                        .disabled(busy)
                    Text(status).font(.footnote).textSelection(.enabled)
                }
            }
            .navigationTitle("Tool installer")
            .alert("Install on Windows laptop?", isPresented: $approve) {
                Button("Install", role: .destructive) { Task { await request(method: "POST", operation: "install") } }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("The bridge will install \(selected) using an approved package source, then verify the executable. Administrator approval may be required.")
            }
        }
    }
    @MainActor private func request(method: String, operation: String) async {
        guard let base = URL(string: endpoint),
              base.scheme == "https", base.host != nil,
              base.user == nil, base.password == nil,
              !token.isEmpty else {
            status = "Configure an HTTPS URL and an authorization token."
            return
        }
        busy = true
        defer { busy = false }
        do {
            let url = base.appendingPathComponent(operation).appending(queryItems: [URLQueryItem(name: "package", value: selected)])
            var req = URLRequest(url: url)
            req.httpMethod = method
            req.timeoutInterval = 120
            req.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
            req.setValue("application/json", forHTTPHeaderField: "Accept")
            if method == "POST" { req.httpBody = Data() }
            let (data, response) = try await URLSession.shared.data(for: req)
            guard let http = response as? HTTPURLResponse, data.count < 128_000 else { throw URLError(.badServerResponse) }
            let body = String(decoding: data, as: UTF8.self)
            status = "HTTP \(http.statusCode): " + String(body.prefix(12000))
        } catch {
            status = "Installer connection failed: " + error.localizedDescription
        }
    }
}
