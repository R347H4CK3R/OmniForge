import Foundation
import ZIPFoundation

/// A deterministic, reproducible first-stage agent. AI may explain the report,
/// but conclusions must remain grounded in these actual tool outputs.
enum AnalysisOrchestrator {
    static func run(_ ipa: URL) throws -> URL {
        let fm = FileManager.default
        let root = fm.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Investigations", isDirectory: true)
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try fm.createDirectory(at: root, withIntermediateDirectories: true)
        var findings: [(String,String)] = []
        let steps: [(String, () throws -> String)] = [
            ("metadata", { try IPAInspector.inspect(ipa) }),
            ("inventory", { try IPAWorkbench.inventory(ipa) }),
            ("architectures", { try IPAWorkbench.executableReport(ipa) }),
            ("reverse_engineering", { try IPAReverseEngineer.report(ipa) }),
            ("signing", { try IPAWorkbench.signingReport(ipa) })
        ]
        for (name,run) in steps {
            do {
                let report = try run()
                try report.write(to: root.appendingPathComponent(name + ".txt"), atomically: true, encoding: .utf8)
                findings.append((name,"complete"))
            } catch {
                let message = "Tool failed: " + error.localizedDescription
                try message.write(to: root.appendingPathComponent(name + ".txt"), atomically: true, encoding: .utf8)
                findings.append((name,"failed: " + error.localizedDescription))
            }
        }
        let summary = (["# OmniForge evidence-driven IPA investigation",
                        "File: " + ipa.lastPathComponent,
                        "All steps are static and read-only. No app code is executed.",
                        "A failed step is reported, not silently treated as success.",
                        ""] + findings.map { "- " + $0.0 + ": " + $0.1 } +
                       ["", "Next: inspect individual reports, then run the authorized GitHub macOS workbench for deeper decompilation.",
                        "Limitations: exact original source and behavior cannot be recovered reliably from compiled binaries."]).joined(separator: "\n")
        try summary.write(to: root.appendingPathComponent("SUMMARY.md"), atomically: true, encoding: .utf8)
        return root
    }
}
