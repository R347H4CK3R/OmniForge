import SwiftUI
import Foundation
import UniformTypeIdentifiers

/// Curated dependency installation through an explicitly trusted HTTPS bridge.
/// No arbitrary model-generated shell commands are accepted.
struct OmniInstallerView: View {
    @AppStorage("installerBridgeURL") private var endpoint = "https://gaminglaptop-1.tail54e01b.ts.net/installer"
    @State private var token = ""
    @State private var importingToken = false
    @State private var hasStoredToken = false
    @ObservedObject private var coordinator = OmniInstallCoordinator.shared
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
                    SecureField("Session authorization token (manual)", text: $token)
                    Button("Choose Token File") { importingToken = true }
                    Text(hasStoredToken ? "Token saved in Keychain" : "No saved token")
                        .font(.caption).foregroundStyle(.secondary)
                    Button("Save Entered Token") {
                        do {
                            try OmniBridgeTokenStore.save(token)
                            token = ""
                            hasStoredToken = true
                            status = "Token securely saved."
                        } catch { status = "Token save failed: " + error.localizedDescription }
                    }.disabled(token.isEmpty)
                    Button("Forget Token", role: .destructive) {
                        do {
                            try OmniBridgeTokenStore.delete()
                            token = ""
                            hasStoredToken = false
                            status = "Token cleared."
                        } catch { status = "Token deletion failed: " + error.localizedDescription }
                    }.disabled(!hasStoredToken)
                    Text("Configure your own HTTPS bridge to the Windows installer service. Do not expose its local HTTP port to the internet.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                if let requested = coordinator.pendingPackage {
                    Section("AI installation request") {
                        Text("OmniForge AI requests installation of: " + requested)
                        Button("Approve and resume AI") { coordinator.decide(true) }
                        Button("Deny", role: .destructive) { coordinator.decide(false) }
                    }
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
.onAppear {
                if endpoint.isEmpty { endpoint = OmniBridgeAddress.restore() ?? "https://gaminglaptop-1.tail54e01b.ts.net/installer" }
                OmniBridgeAddress.save(endpoint)
                hasStoredToken = OmniBridgeTokenStore.load() != nil
            }
            .onChange(of: endpoint) { newValue in OmniBridgeAddress.save(newValue) }
            .navigationTitle("Tool installer")
            .fileImporter(isPresented: $importingToken, allowedContentTypes: [.plainText, .data]) { result in
                do {
                    try OmniBridgeTokenStore.importFile(try result.get())
                    token = ""
                    hasStoredToken = true
                    status = "Token imported to Keychain. You may delete the original token file from Files."
                } catch { status = "Token import failed: " + error.localizedDescription }
            }
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
              OmniBridgeTokenStore.load() != nil else {
            status = "Configure an HTTPS URL and an authorization token."
            return
        }
        coordinator.setSessionToken("")
        busy = true
        defer { busy = false }
        do {
            let url = base.appendingPathComponent(operation).appending(queryItems: [URLQueryItem(name: "package", value: selected)])
            var req = URLRequest(url: url)
            req.httpMethod = method
            req.timeoutInterval = 120
            req.setValue("Bearer " + (OmniBridgeTokenStore.load() ?? ""), forHTTPHeaderField: "Authorization")
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
