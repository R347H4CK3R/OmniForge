import Foundation
import ZIPFoundation

/// Read-only static analysis of user-provided IPA archives. No execution or bypass.
enum IPAReverseEngineer {
    private static func fail(_ message: String) -> NSError {
        NSError(domain: "OmniForge.ReverseEngineering", code: 1,
                userInfo: [NSLocalizedDescriptionKey: message])
    }
    private static func safe(_ path: String) -> Bool {
        !path.isEmpty && !path.hasPrefix("/") && !path.contains("\\") &&
        !path.contains("\0") && !path.split(separator: "/").contains("..")
    }
    static func report(_ url: URL) throws -> String {
        let archive = try Archive(url: url, accessMode: .read)
        var result: [String] = ["IPA REVERSE-ENGINEERING REPORT", "Archive: \(url.lastPathComponent)"]
        var entries = 0
        var binaries = 0
        var stringsFound = 0
        var accumulated: UInt64 = 0
        for entry in archive {
            entries += 1
            guard entries <= 150_000, safe(entry.path) else { throw fail("Unsafe or excessive IPA entries") }
            let ext = URL(fileURLWithPath: entry.path).pathExtension.lowercased()
            if entry.path.contains(".framework/") && entry.path.hasSuffix("/Info.plist") {
                result.append("Framework: \(entry.path)")
            }
            guard entry.type == .file, entry.path.hasPrefix("Payload/"),
                  entry.uncompressedSize >= 32,
                  entry.uncompressedSize <= 30_000_000 else { continue }
            guard !["gguf","car","png","jpeg","jpg","webp","metallib","mp4","m4a","wav"].contains(ext) else { continue }
            // Bounding total inflation prevents unbounded memory or CPU usage.
            accumulated += UInt64(entry.uncompressedSize)
            guard accumulated <= 150_000_000 else { break }
            var data = Data()
            _ = try archive.extract(entry, consumer: { chunk in
                guard data.count + chunk.count <= 30_000_000 else { throw fail("Binary exceeds inspection limit") }
                data.append(chunk)
            })
            guard data.count >= 8 else { continue }
            let magic = [UInt8](data.prefix(4))
            let isMachO = magic == [0xcf,0xfa,0xed,0xfe] || magic == [0xfe,0xed,0xfa,0xcf] ||
                magic == [0xca,0xfe,0xba,0xbe] || magic == [0xbe,0xba,0xfe,0xca]
            guard isMachO else { continue }
            binaries += 1
            result.append("Mach-O: \(entry.path) — \(data.count) bytes")
            if magic == [0xcf,0xfa,0xed,0xfe] {
                let cpu = data[4..<8].enumerated().reduce(UInt32(0)) { $0 | (UInt32($1.element) << (UInt32($1.offset) * 8)) }
                result.append("CPU type: \(cpu == 0x0100000c ? "ARM64" : String(format: "0x%08x", cpu))")
            }
            var current: [UInt8] = []
            var selected: [String] = []
            for byte in data {
                if byte >= 32 && byte <= 126 {
                    if current.count < 240 { current.append(byte) }
                } else {
                    if current.count >= 8, selected.count < 80 {
                        let text = String(decoding: current, as: UTF8.self)
                        if text.contains("/") || text.contains(".") || text.contains("swift") ||
                            text.contains("objc") || text.contains("error") || text.contains("http") {
                            selected.append(text)
                        }
                    }
                    current.removeAll(keepingCapacity: true)
                }
            }
            stringsFound += selected.count
            result.append(contentsOf: selected.map { "  string: \($0)" })
            if binaries >= 8 { break }
        }
        result.insert("Inspected Mach-O binaries: \(binaries) | Selected strings: \(stringsFound)", at: 2)
        result.append("Static analysis only. For detailed ARM64 disassembly, use the GitHub macOS IPA Workbench.")
        result.append("Compiled binaries cannot reliably be converted back into the original Swift source.")
        return result.joined(separator: "\n")
    }
}
