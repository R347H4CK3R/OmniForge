import SwiftUI

struct ProjectReadinessView: View {
    @EnvironmentObject var store: AssistantStore
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var readiness = ProjectReadinessStore()

    var body: some View {
        List {
            Section {
                Label("Read-only host snapshot", systemImage: "checklist")
                    .font(.headline)
                Text("Detection is not a successful build. No builds, updates or installations are started.")
                    .font(.footnote).foregroundStyle(.secondary)
                Button("Refresh host readiness") { readiness.refresh(endpoint: store.onlineEndpoint) }
                    .disabled(readiness.loading)
                if readiness.loading { ProgressView("Reading host…") }
                Text(readiness.message).font(.footnote).textSelection(.enabled)
            }
            if let report = readiness.report {
                if report.scan.truncated || !report.scan.blockers.isEmpty {
                    Section("Partial scan") {
                        if report.scan.truncated { Text("Entry limit reached. Some projects may not be shown.") }
                        ForEach(Array(report.scan.blockers.enumerated()), id: \.offset) { _, blocker in Text(blocker) }
                    }
                }
                Section("Workspace projects") {
                    if report.projects.isEmpty { Text("No supported projects detected in the scanned workspace.") }
                    ForEach(Array(report.projects.enumerated()), id: \.offset) { _, project in
                        VStack(alignment: .leading, spacing: 10) {
                            Text(project.path == "." ? "Workspace root" : project.path).font(.headline)
                            ForEach(Array(project.targets.enumerated()), id: \.offset) { _, target in
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(target.platform.uppercased()).font(.subheadline.bold())
                                    Label(status(target.status), systemImage: target.status == "blocked" ? "exclamationmark.triangle" : "info.circle")
                                        .foregroundStyle(target.status == "blocked" ? Color.orange : Color.secondary)
                                    Text("Build unverified").font(.caption).foregroundStyle(.secondary)
                                    ForEach(Array(target.blockers.enumerated()), id: \.offset) { _, blocker in Text(blocker).font(.footnote) }
                                }
                            }
                        }.padding(.vertical, 4)
                    }
                }
                Section("Remote Mac") {
                    Text(report.remote_mac.status.replacingOccurrences(of: "_", with: " ").capitalized)
                    if let blocker = report.remote_mac.blocker { Text(blocker).font(.footnote) }
                    Text("Build unverified").font(.caption).foregroundStyle(.secondary)
                }
                Section("Stored job queue") {
                    Text(report.queue.status.replacingOccurrences(of: "_", with: " ").capitalized)
                    Text("Stored statuses only. Worker liveness and build success are not verified.").font(.footnote)
                    if let blocker = report.queue.blocker { Text(blocker).font(.footnote) }
                    if report.queue.jobs.isEmpty { Text("No stored jobs shown.") }
                    ForEach(Array(report.queue.jobs.enumerated()), id: \.offset) { _, job in
                        VStack(alignment: .leading) {
                            Text(job.id).font(.caption.monospaced())
                            Text("\(job.status) · attempts: \(job.attempts)")
                        }
                    }
                    if report.queue.truncated { Text("Only the latest 30 jobs are shown.").font(.footnote) }
                }
            }
        }
        .navigationTitle("Host readiness")
        .onDisappear { readiness.cancel() }
        .onChange(of: store.onlineEndpoint) { _, _ in readiness.cancel() }
        .onChange(of: scenePhase) { _, phase in if phase != .active { readiness.cancel() } }
    }
    private func status(_ value: String) -> String {
        switch value {
        case "blocked": return "Blocked"
        case "prerequisites_detected": return "Prerequisites detected"
        default: return "Unknown readiness"
        }
    }
}
