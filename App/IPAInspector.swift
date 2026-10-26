import Foundation
import ZIPFoundation

enum IPAInspector {
    static func inspect(_ url: URL) throws -> String {
        let archive = try Archive(url: url, accessMode: .read)
        var count = 0
        var executables: [String] = []
        var frameworks: [String] = []
        var mainPlist: Entry?
        for entry in archive {
            count += 1
            if count > 150_000 { throw NSError(domain: "OmniForge", code: 41, userInfo: [NSLocalizedDescriptionKey: "IPA has too many entries"]) }
            let path = entry.path
            if path.hasPrefix("Payload/") && path.hasSuffix(".app/Info.plist") &&
               path.components(separatedBy: "/").count == 3 { mainPlist = entry }
            if path.contains(".framework/") && path.hasSuffix(".framework/Info.plist") { frameworks.append(path) }
            if path.hasPrefix("Payload/") && path.hasSuffix(".app/") { executables.append(path) }
        }
        guard let plist = mainPlist else {
            throw NSError(domain: "OmniForge", code: 42, userInfo: [NSLocalizedDescriptionKey: "IPA missing Payload/App.app/Info.plist"])
        }
        guard plist.uncompressedSize <= 2_000_000 else {
            throw NSError(domain: "OmniForge", code: 43, userInfo: [NSLocalizedDescriptionKey: "Info.plist exceeds safe limit"])
        }
        var plistData = Data()
        _ = try archive.extract(plist, consumer: { chunk in
            guard plistData.count + chunk.count <= 2_000_000 else {
                throw NSError(domain: "OmniForge", code: 44, userInfo: [NSLocalizedDescriptionKey: "Info.plist too large"])
            }
            plistData.append(chunk)
        })
        let object = try PropertyListSerialization.propertyList(from: plistData, format: nil)
        guard let info = object as? [String: Any] else {
            throw NSError(domain: "OmniForge", code: 45, userInfo: [NSLocalizedDescriptionKey: "Invalid app metadata"])
        }
        let keys = ["CFBundleDisplayName", "CFBundleName", "CFBundleIdentifier", "CFBundleShortVersionString",
                    "CFBundleVersion", "MinimumOSVersion", "CFBundleExecutable", "UIDeviceFamily"]
        let fields = keys.map { key in "\(key): \(info[key].map { String(describing: $0) } ?? "Unknown")" }
        return (["IPA: \(url.lastPathComponent)", "Entries: \(count)", "Framework metadata entries: \(frameworks.count)",
                 "App directories: \(executables.count)"] + fields +
                 ["Inspection only. Original source code cannot be recovered reliably from an IPA."]).joined(separator: "\n")
    }
}
