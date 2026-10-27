import Foundation
import CryptoKit

/// Explicit capabilities. Tool execution is deterministic; model text does not grant capabilities.
enum OmniToolCatalog {
    static let help = """
    OmniForge tools (free, no paid API required):
    /tools — show this list
    /self-test — run local and paired Windows diagnostics\n    /selftest — alias
    /web https://example.org — retrieve a public HTTPS page (requires internet)
    /search your query — search via configured SearXNG instance
    /sha256 text — SHA-256 of the supplied text (offline)
    /base64 text — Base64-encode text (offline)
    /unbase64 text — decode Base64 as UTF-8 (offline)
    /json text — validate and pretty-print JSON (offline)
    /device — show app/device environment information (offline)
    IPA inspector — select a file in the Rebuild tab (offline)
    Local GGUF chat — requires an imported model (offline)
    Ollama chat — connect to your own HTTPS server (optional)
    Ghidra, Xcode, and GitHub Actions — run on authorized remote machines via workflows, not inside iOS.

    Not currently integrated: ChatGPT proprietary tools, account connectors, arbitrary shell execution, general web search, autonomous plugin installation, or guaranteed app-source recovery.
    """
    static func handles(_ prompt: String) -> Bool {
        ["/tools","/self-test","/selftest","/device","/web ","/search ","/sha256 ","/base64 ","/unbase64 ","/json "]
            .contains { prompt == $0 || prompt.hasPrefix($0) }
    }
    private static func runSelfTest() -> String {
        let fm = FileManager.default
        let folder = fm.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("AgentWorkspace", isDirectory: true)
        let file = folder.appendingPathComponent(".omniforge-selftest-" + UUID().uuidString + ".json")
        defer { try? fm.removeItem(at: file) }
        do {
            try fm.createDirectory(at: folder, withIntermediateDirectories: true)
            let payload = Data(#"{"test":"omniforge","ok":true}"#.utf8)
            try payload.write(to: file, options: .atomic)
            let readback = try Data(contentsOf: file)
            guard readback == payload else { return "FAIL: Written bytes did not match readback." }
            let parsed = try JSONSerialization.jsonObject(with: readback) as? [String: Any]
            guard parsed?["ok"] as? Bool == true,
                  parsed?["test"] as? String == "omniforge" else {
                return "FAIL: JSON data validation failed."
            }
            let listing = try fm.contentsOfDirectory(atPath: folder.path)
            guard listing.contains(file.lastPathComponent) else {
                return "FAIL: Workspace listing did not show written file."
            }
            return "PASS: Workspace created; file written; file listed; bytes read and matched; JSON decoded. Temporary test file scheduled for removal."
        } catch {
            return "FAIL: " + error.localizedDescription
        }
    }
    static func execute(_ prompt: String) async throws -> String {
        if prompt == "/tools" { return help }
        if prompt == "/selftest" || prompt == "/self-test" { return await OmniSelfTest.run(local: runSelfTest()) }
        if prompt == "/device" {
            let bundle = Bundle.main
            return "Bundle ID: \(bundle.bundleIdentifier ?? "unknown")\nVersion: \(bundle.object(forInfoDictionaryKey: "CFBundleShortVersionString") ?? "?")\nBuild: \(bundle.object(forInfoDictionaryKey: "CFBundleVersion") ?? "?")\nRuntime: iOS sandbox; no arbitrary external executables."
        }
        if prompt.hasPrefix("/search ") {
            return try await OmniSearch.search(String(prompt.dropFirst(8)))
        }
        if prompt.hasPrefix("/web ") {
            return try await ExternalToolRuntime.fetchPage(String(prompt.dropFirst(5)).trimmingCharacters(in: .whitespacesAndNewlines))
        }
        let pair = prompt.split(separator: " ", maxSplits: 1, omittingEmptySubsequences: false)
        guard pair.count == 2 else { return "Supply text after the command. Use /tools to see examples." }
        let value = String(pair[1])
        switch String(pair[0]) {
        case "/sha256":
            return SHA256.hash(data: Data(value.utf8)).map { String(format:"%02x",$0) }.joined()
        case "/base64":
            return Data(value.utf8).base64EncodedString()
        case "/unbase64":
            guard let bytes=Data(base64Encoded:value), let text=String(data:bytes,encoding:.utf8)
            else { return "Invalid Base64 UTF-8 input." }
            return text
        case "/json":
            let input=Data(value.utf8)
            let object=try JSONSerialization.jsonObject(with:input,options:[.fragmentsAllowed])
            let formatted=try JSONSerialization.data(withJSONObject:object,options:[.prettyPrinted,.sortedKeys,.fragmentsAllowed])
            return String(decoding:formatted,as:UTF8.self)
        default: return "Unknown command. Type /tools."
        }
    }
}
