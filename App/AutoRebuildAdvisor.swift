import Foundation
import ZIPFoundation

enum AutoRebuildAdvisor {
    static func report(for ipa: URL) throws -> String {
        guard let archive = Archive(url: ipa, accessMode: .read) else {
            throw NSError(domain:"OmniForge.AutoRebuild",code:1,userInfo:[NSLocalizedDescriptionKey:"Unable to read IPA archive"])
        }
        let allowed: Set<String> = ["json","plist","strings","txt","cfg","ini","xml","png","jpg","jpeg","webp","svg"]
        var count=0
        var patches:[String]=[]
        var appPlists:[String]=[]
        for entry in archive {
            count += 1
            if count > 150_000 { throw NSError(domain:"OmniForge.AutoRebuild",code:2,userInfo:[NSLocalizedDescriptionKey:"IPA has too many entries"]) }
            let path=entry.path
            guard !path.hasPrefix("/"), !path.contains("\\"),
                  !path.split(separator:"/").contains("..") else {
                throw NSError(domain:"OmniForge.AutoRebuild",code:3,userInfo:[NSLocalizedDescriptionKey:"Unsafe IPA entry"])
            }
            if path.hasPrefix("Payload/") && path.hasSuffix(".app/Info.plist") { appPlists.append(path) }
            let ext=URL(fileURLWithPath:path).pathExtension.lowercased()
            if allowed.contains(ext), entry.type == .file, entry.uncompressedSize <= 50_000_000, patches.count < 30 {
                patches.append(path)
            }
        }
        guard !appPlists.isEmpty else {
            throw NSError(domain:"OmniForge.AutoRebuild",code:4,userInfo:[NSLocalizedDescriptionKey:"Missing application bundle"])
        }
        let paths=patches.joined(separator:"\n")
        return """
        AUTOMATIC REBUILD PATH ASSESSMENT
        IPA: \(ipa.lastPathComponent)
        Entries: \(count)
        Original source: not recoverable from binary alone.

        1. AUTHORIZED SOURCE PROJECT
        Supply the application's actual source repository if available; OmniForge cannot infer or authenticate its location from the IPA alone.

        2. COMPILABLE CLEAN-ROOM PROJECT
        Supported via GitHub IPA Workbench: creates original SwiftUI scaffolding from metadata, inventories and screenshots. The generated starter compiles but does NOT recreate game or app logic.

        3. RESOURCE-ONLY IPA PATCH
        \(patches.isEmpty ? "No supported resource candidates found." : "Found \(patches.count) candidate paths (first 30):\n" + paths)
        Resource changes invalidate the original signature and require re-signing.

        NEXT: Use Rebuild → Generate editable SwiftUI project for workflow, or Replace resource in IPA for supported files.
        """
    }
}
