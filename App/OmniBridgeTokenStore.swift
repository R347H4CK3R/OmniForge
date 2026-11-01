import Foundation
import Security

/// Stores only the installer bridge credential in the device Keychain.
/// No token is logged, included in model prompts, or saved to UserDefaults.
enum OmniBridgeTokenStore {
    private static let service = "com.r347h4ck3r.omniforge.installer"
    private static let account = "session-token"

    static func load() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data,
              let text = String(data: data, encoding: .utf8) else { return nil }
        return text
    }

    static func save(_ value: String) throws {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.utf8.count >= 32, trimmed.utf8.count <= 4096,
              !trimmed.contains(where: { $0.isWhitespace || $0.isNewline }) else {
            throw NSError(domain: "OmniForge.Token", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Invalid token format or length."])
        }
        let identity: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        let changes: [String: Any] = [kSecValueData as String: Data(trimmed.utf8),
                                      kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]
        let update = SecItemUpdate(identity as CFDictionary, changes as CFDictionary)
        if update == errSecItemNotFound {
            let query = identity.merging(changes) { _, new in new }
            let status = SecItemAdd(query as CFDictionary, nil)
            guard status == errSecSuccess else { throw NSError(domain: NSOSStatusErrorDomain, code: Int(status)) }
        } else if update != errSecSuccess {
            throw NSError(domain: NSOSStatusErrorDomain, code: Int(update))
        }
    }

    static func delete() throws {
        let status = SecItemDelete([
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ] as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw NSError(domain: NSOSStatusErrorDomain, code: Int(status))
        }
    }

    static func importFile(_ url: URL) throws {
        let scope = url.startAccessingSecurityScopedResource()
        defer { if scope { url.stopAccessingSecurityScopedResource() } }
        let data = try Data(contentsOf: url, options: [.mappedIfSafe])
        guard data.count <= 4096, let token = String(data: data, encoding: .utf8) else {
            throw NSError(domain: "OmniForge.Token", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "Token file must be UTF-8 text under 4 KB."])
        }
        try save(token)
    }
}
