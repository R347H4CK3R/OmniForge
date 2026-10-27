import Foundation
import SwiftUI

/// Checks published GitHub Actions build status only. Never downloads or executes code.
@MainActor
final class OmniForgeUpdates: ObservableObject {
    @Published var updateAvailable = false
    @Published var checking = false
    @Published var status = "Not checked"
    @Published var buildURL: URL?
    @Published var availableBuild: Int?
    private let endpoint = URL(string: "https://api.github.com/repos/R347H4CK3R/OmniForge/actions/workflows/ios-unsigned.yml/runs?branch=main&status=success&per_page=1")!

    var installedBuild: Int {
        Int(Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "0") ?? 0
    }

    func check() async {
        guard !checking else { return }
        checking = true
        defer { checking = false }
        do {
            var request = URLRequest(url: endpoint)
            request.timeoutInterval = 20
            request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            let result = try JSONDecoder().decode(WorkflowResponse.self, from: data)
            guard let run = result.workflow_runs.first,
                  run.conclusion == "success",
                  let url = URL(string: run.html_url),
                  url.host == "github.com" else {
                status = "No successful published build found"
                updateAvailable = false
                return
            }
            availableBuild = run.run_number
            buildURL = url
            updateAvailable = run.run_number > installedBuild
            status = updateAvailable
                ? "Build #\\(run.run_number) available — signed installation required"
                : "Current or newer build installed"
        } catch {
            status = "Unable to check updates: \\(error.localizedDescription)"
        }
    }
}

private struct WorkflowResponse: Decodable {
    let workflow_runs: [WorkflowRun]
}
private struct WorkflowRun: Decodable {
    let run_number: Int
    let conclusion: String?
    let html_url: String
}
