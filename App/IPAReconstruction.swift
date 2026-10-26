import Foundation
import ZIPFoundation

/// Offline project reconstruction produces a documented inventory, not original source.
enum IPAReconstruction {
    static func generateReport(_ url: URL) throws -> URL {
        let archive = try Archive(url: url, accessMode: .read)
        var files: [String] = []
        var plist: [String: Any] = [:]
        var count = 0
        for entry in archive {
            count += 1
            guard count <= 150_000 else { throw failure("Archive has too many entries") }
            guard safe(entry.path) else { throw failure("Unsafe archive path") }
            if files.count < 1000 { files.append(entry.path) }
            if entry.path.hasPrefix("Payload/") && entry.path.hasSuffix(".app/Info.plist") &&
                entry.path.split(separator: "/").count == 3 && entry.uncompressedSize < 2_000_000 {
                var data = Data()
                _ = try archive.extract(entry, consumer: { chunk in
                    guard data.count + chunk.count <= 2_000_000 else { throw failure("Plist exceeded limit") }
                    data.append(chunk)
                })
                plist = (try? PropertyListSerialization.propertyList(from: data, format: nil)) as? [String: Any] ?? [:]
            }
        }
        let root = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Reconstructions", isDirectory: true)
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let bundle = plist["CFBundleIdentifier"] as? String ?? "unknown"
        let display = plist["CFBundleDisplayName"] as? String ?? plist["CFBundleName"] as? String ?? "Imported App"
        let readme = """
        # Reconstructed Application Inventory

        Name: \(display)
        Bundle ID: \(bundle)
        Original IPA: \(url.lastPathComponent)

        This is a partial analysis scaffold, NOT recovered original Swift/Objective-C source.
        Compiled app logic, signing credentials, and proprietary project configuration cannot be reconstructed reliably.
        Work only with software you have permission to inspect or modify.

        ## Next steps
        Implement an original SwiftUI application using this inventory, user-owned assets, and observed behavior.
        Review third-party assets and code licenses before redistribution.

        ## Archive contents (first 1000 entries)
        \(files.joined(separator: "\n"))
        """
        try readme.write(to: root.appendingPathComponent("README.md"), atomically: true, encoding: .utf8)
        let data: [String: String] = ["displayName": display, "bundleIdentifier": bundle, "sourceIPA": url.lastPathComponent]
        let json = try JSONSerialization.data(withJSONObject: data, options: [.prettyPrinted, .sortedKeys])
        try json.write(to: root.appendingPathComponent("metadata.json"), options: .atomic)
        return root
    }
    private static func safe(_ path: String) -> Bool {
        !path.hasPrefix("/") && !path.contains("\\") && !path.contains("\0") &&
        !path.split(separator: "/").contains("..")
    }
    private static func failure(_ text: String) -> NSError {
        NSError(domain: "OmniForge.Reconstruction", code: 99, userInfo: [NSLocalizedDescriptionKey: text])
    }
}
