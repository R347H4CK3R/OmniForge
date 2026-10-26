import Foundation
import ZIPFoundation
import CryptoKit

/// User-authorized archive examination and resource export. Does not execute IPA code.
enum IPAWorkbench {
    static func inventory(_ url: URL) throws -> String {
        let archive = try Archive(url: url, accessMode: .read)
        var rows: [String] = []
        var count = 0
        var total: UInt64 = 0
        for entry in archive {
            count += 1
            if count > 150_000 { throw failure("Too many archive entries") }
            guard isSafe(entry.path) else { throw failure("Unsafe path in IPA: \(entry.path)") }
            let size = UInt64(entry.uncompressedSize)
            if size > 2_000_000_000 { throw failure("Oversized archive entry") }
            total += size
            if total > 12_000_000_000 { throw failure("Expanded IPA exceeds safety limit") }
            if rows.count < 500 { rows.append("\(entry.type == .directory ? "DIR " : "FILE") \(size) \(entry.path)") }
        }
        return (["IPA INVENTORY: \(url.lastPathComponent)", "Entries: \(count)", "Expanded size: \(total) bytes"] + rows +
                (count > rows.count ? ["... \(count - rows.count) more entries"] : [])).joined(separator: "\n")
    }

    static func executableReport(_ url: URL) throws -> String {
        let archive = try Archive(url: url, accessMode: .read)
        var report = [String]()
        var candidates = 0
        for entry in archive {
            guard isSafe(entry.path) else { throw failure("Unsafe archive entry") }
            guard entry.type == .file, entry.uncompressedSize >= 32,
                  entry.uncompressedSize < 500_000_000,
                  entry.path.hasPrefix("Payload/"),
                  (entry.path.contains(".app/") || entry.path.contains(".framework/")) else { continue }
            let lower = entry.path.lowercased()
            if lower.hasSuffix(".png") || lower.hasSuffix(".jpg") || lower.hasSuffix(".json") ||
               lower.hasSuffix(".plist") || lower.hasSuffix(".metallib") || lower.hasSuffix(".car") ||
               lower.hasSuffix(".nib") || lower.hasSuffix(".storyboardc") || lower.hasSuffix(".gguf") { continue }
            let header = try readEntry(entry, archive: archive, maxBytes: 64, prefixOnly: true)
            guard header.count >= 8 else { continue }
            let bytes = [UInt8](header)
            let magic = bytes.prefix(4).map { String(format: "%02x", $0) }.joined()
            guard ["feedfacf", "cffaedfe", "cafebabe", "bebafeca"].contains(magic) else { continue }
            candidates += 1
            report.append("Mach-O: \(entry.path) (\(entry.uncompressedSize) bytes, magic \(magic))")
            if candidates >= 80 { break }
        }
        return (["MACH-O REPORT", "Identified executables: \(candidates)"] + report +
                ["Executable inspection is structural. It cannot reconstruct original Swift/Objective-C source."]).joined(separator: "\n")
    }

    static func exportResources(_ url: URL, destination: URL) throws -> Int {
        let archive = try Archive(url: url, accessMode: .read)
        try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
        let base = destination.standardizedFileURL
        var count = 0
        var total: UInt64 = 0
        let allowed = Set(["json", "plist", "strings", "stringsdict", "txt", "md", "cfg", "ini", "xml", "png", "jpg", "jpeg", "webp", "svg", "lproj"])
        for entry in archive {
            guard isSafe(entry.path) else { throw failure("Unsafe entry path") }
            guard entry.type == .file else { continue }
            let ext = URL(fileURLWithPath: entry.path).pathExtension.lowercased()
            guard allowed.contains(ext), entry.uncompressedSize <= 50_000_000 else { continue }
            total += UInt64(entry.uncompressedSize)
            if total > 500_000_000 { throw failure("Resource export exceeds 500 MB") }
            let target = base.appendingPathComponent(entry.path).standardizedFileURL
            guard target.path.hasPrefix(base.path + "/") else { throw failure("Path escapes destination") }
            try FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
            let data = try readEntry(entry, archive: archive, maxBytes: 50_000_000)
            try data.write(to: target, options: .atomic)
            count += 1
        }
        return count
    }

    private static func readEntry(_ entry: Entry, archive: Archive, maxBytes: Int, prefixOnly: Bool = false) throws -> Data {
        guard entry.type == .file else { return Data() }
        if !prefixOnly && entry.uncompressedSize > UInt64(maxBytes) { throw failure("Entry too large") }
        var data = Data()
        _ = try archive.extract(entry, consumer: { chunk in
            if !prefixOnly && data.count + chunk.count > maxBytes { throw failure("Entry expanded beyond limit") }
            if data.count < maxBytes { data.append(contentsOf: chunk.prefix(maxBytes - data.count)) }
        })
        return data
    }
    private static func isSafe(_ path: String) -> Bool {
        !path.isEmpty && !path.hasPrefix("/") && !path.contains("\\") &&
        !path.split(separator: "/").contains("..") && !path.contains("\0")
    }
    private static func failure(_ message: String) -> NSError {
        NSError(domain: "OmniForge.IPA", code: 88, userInfo: [NSLocalizedDescriptionKey: message])
    }
}
