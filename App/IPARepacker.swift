import Foundation
import ZIPFoundation

/// Creates a separate unsigned IPA with one supported non-executable resource replaced.
enum IPARepacker {
    static func replaceResource(ipa: URL, archivePath: String, replacement: URL) throws -> URL {
        guard safe(archivePath), archivePath.hasPrefix("Payload/") else { throw failure("Unsafe archive path") }
        let allowed = Set(["json","plist","strings","stringsdict","txt","md","cfg","ini","xml","png","jpg","jpeg","webp","svg"])
        guard allowed.contains(URL(fileURLWithPath: archivePath).pathExtension.lowercased()) else {
            throw failure("Only supported non-executable resources may be replaced")
        }
        let attr = try FileManager.default.attributesOfItem(atPath: replacement.path)
        guard (attr[.size] as? NSNumber)?.int64Value ?? 0 <= 50_000_000 else { throw failure("Replacement exceeds 50 MB") }
        let folder = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("Repacked", isDirectory: true)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        let target = folder.appendingPathComponent(UUID().uuidString + ".ipa")
        try FileManager.default.copyItem(at: ipa, to: target)
        do {
            guard let archive = Archive(url: target, accessMode: .update) else { throw failure("Unable to open IPA for update") }
            guard let existing = archive[archivePath] else { throw failure("Resource not found inside IPA") }
            try archive.remove(existing)
            try archive.addEntry(with: archivePath, fileURL: replacement, compressionMethod: .deflate)
            // The signature is no longer valid after changing a resource. This file is unsigned/invalidly signed.
            return target
        } catch {
            try? FileManager.default.removeItem(at: target)
            throw error
        }
    }
    private static func safe(_ path: String) -> Bool {
        !path.isEmpty && !path.hasPrefix("/") && !path.contains("\\") && !path.contains("\0") &&
        !path.split(separator: "/").contains("..")
    }
    private static func failure(_ text: String) -> NSError {
        NSError(domain: "OmniForge.Repacker", code: 78, userInfo: [NSLocalizedDescriptionKey: text])
    }
}
