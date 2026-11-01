import Foundation

/// A user-visible backup of the non-secret remote address.
/// UserDefaults/@AppStorage is primary; this file recovers from preference resets.
enum OmniBridgeAddress {
    private static var file: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("OmniForgeBridgeAddress.txt")
    }
    static func save(_ address: String) {
        guard let url = URL(string: address), url.scheme == "https",
              url.host != nil, url.user == nil, url.password == nil else { return }
        try? Data(address.utf8).write(to: file, options: [.atomic, .completeFileProtectionUnlessOpen])
    }
    static func restore() -> String? {
        guard let value = try? String(contentsOf: file, encoding: .utf8)
            .trimmingCharacters(in: .whitespacesAndNewlines),
              let url = URL(string: value), url.scheme == "https", url.host != nil,
              url.user == nil, url.password == nil else { return nil }
        return value
    }
}
