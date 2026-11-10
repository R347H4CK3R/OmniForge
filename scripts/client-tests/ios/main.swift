// Run: swiftc App/ProjectReadiness.swift scripts/client-tests/ios/main.swift -o /tmp/readiness-test && /tmp/readiness-test
import Foundation

func reject(_ value: String) {
    do { _ = try ProjectReadiness.endpoint(value); fatalError("Unsafe endpoint accepted") } catch {}
}
let actual = try ProjectReadiness.endpoint("https://host.test:8443/proxy/v1/chat/completions/")
precondition(actual.absoluteString == "https://host.test:8443/proxy/v1/projects")
let encoded = try ProjectReadiness.endpoint("https://host.test/a%20b/v1/chat/completions")
precondition(encoded.absoluteString == "https://host.test/a%20b/v1/projects")
for value in ["http://host.test/v1/chat/completions", "https://secret@host.test/v1/chat/completions", "https://host.test/v1/chat/completions?key=x", "https://host.test/v1/chat/completions#x", "https://host.test/other"] { reject(value) }
let empty = #"{"schema":1,"generated_at":"today","read_only":true,"execution_enabled":false,"scan":{"truncated":false,"blockers":[]},"projects":[],"queue":{"status":"not_initialized","jobs":[],"truncated":false},"remote_mac":{"status":"not_configured"}}"#
let report = try ProjectReadiness.decode(Data(empty.utf8))
precondition(report.projects.isEmpty && report.remote_mac.status == "not_configured")
do { _ = try ProjectReadiness.decode(Data(empty.replacingOccurrences(of: "\"schema\":1", with: "\"schema\":2").utf8)); fatalError("Unknown schema accepted") } catch {}
do { _ = try ProjectReadiness.decode(Data("{}".utf8)); fatalError("Missing fields accepted") } catch {}
do { _ = try ProjectReadiness.decode(Data(repeating: 32, count: 524289)); fatalError("Oversized report accepted") } catch {}
print("iOS dashboard URL and report policy checks passed")
