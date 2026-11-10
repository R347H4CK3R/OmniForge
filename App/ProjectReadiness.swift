import Foundation

/// Pure report/URL policy, independent of the model client and installer bridge.
enum ProjectReadiness {
    static func endpoint(_ address: String) throws -> URL {
        guard var parts = URLComponents(string: address.trimmingCharacters(in: .whitespacesAndNewlines)),
              parts.scheme == "https", let host = parts.host, !host.isEmpty,
              parts.user == nil, parts.password == nil, parts.query == nil, parts.fragment == nil else {
            throw Failure.message("Set a valid HTTPS AI endpoint without URL credentials, query or fragment in Settings.")
        }
        var path = parts.percentEncodedPath
        while path.hasSuffix("/") { path.removeLast() }
        // Preserve the reverse-proxy prefix of the existing completion endpoint.
        guard path.hasSuffix("/v1/chat/completions") else {
            throw Failure.message("The saved AI endpoint must end in /v1/chat/completions to locate host readiness.")
        }
        path.removeLast("/v1/chat/completions".count)
        parts.percentEncodedPath = path + "/v1/projects"
        guard let url = parts.url else { throw Failure.message("Invalid host address.") }
        return url
    }
    enum Failure: LocalizedError {
        case message(String)
        var errorDescription: String? { if case let .message(text) = self { return text }; return nil }
    }
    struct Report: Decodable {
        let schema: Int
        let generated_at: String
        let read_only: Bool
        let execution_enabled: Bool
        let scan: Scan
        let projects: [Project]
        let queue: Queue
        let remote_mac: Mac
    }
    struct Scan: Decodable { let truncated: Bool; let blockers: [String] }
    struct Project: Decodable { let path: String; let targets: [Target] }
    struct Target: Decodable { let platform: String; let status: String; let blockers: [String]; let build_verified: Bool }
    struct Queue: Decodable { let status: String; let jobs: [Job]; let truncated: Bool; let blocker: String? }
    struct Job: Decodable { let id: String; let status: String; let attempts: Int }
    struct Mac: Decodable { let status: String; let blocker: String? }
    static func decode(_ data: Data) throws -> Report {
        guard data.count <= 524288 else { throw Failure.message("Readiness report exceeds the size limit.") }
        let report = try JSONDecoder().decode(Report.self, from: data)
        guard report.schema == 1, report.read_only, !report.execution_enabled,
              report.projects.count <= 101, report.queue.jobs.count <= 30,
              report.projects.allSatisfy({ $0.targets.count <= 16 }) else {
            throw Failure.message("Unsupported readiness report. Update the host service separately.")
        }
        return report
    }
}
