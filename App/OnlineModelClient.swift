import Foundation
import Security

enum OnlineModelClient {
    static func respond(endpoint: String, model: String, messages: [ChatLine]) async throws -> String {
        guard let url = URL(string: endpoint), url.scheme == "https",
              url.user == nil, url.password == nil,
              url.host != nil, !model.trimmingCharacters(in: .whitespaces).isEmpty else {
            throw NSError(domain:"OmniForge.Online",code:1,userInfo:[NSLocalizedDescriptionKey:"Configure an HTTPS chat completions endpoint and model ID"])
        }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.timeoutInterval = 120
        req.setValue("application/json", forHTTPHeaderField:"Content-Type")
        if let token = readKey() , !token.isEmpty {
            req.setValue("Bearer " + token, forHTTPHeaderField:"Authorization")
        }
        struct Message: Encodable { let role: String; let content: String }
        struct Payload: Encodable { let model: String; let messages: [Message]; let stream: Bool }
        let history = messages.suffix(16).map { Message(role: $0.role, content: String($0.text.prefix(16000))) }
        req.httpBody = try JSONEncoder().encode(Payload(model:model,messages:history,stream:false))
        let (data,response) = try await URLSession.shared.data(for:req)
        guard let status = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        guard (200..<300).contains(status.statusCode) else {
            throw NSError(domain:"OmniForge.Online",code:status.statusCode,userInfo:[NSLocalizedDescriptionKey:"Online server returned HTTP \(status.statusCode)"])
        }
        struct Reply: Decodable {
            struct Choice: Decodable {
                struct ResponseMessage: Decodable { let content: String? }
                let message: ResponseMessage
            }
            let choices: [Choice]
        }
        let parsed = try JSONDecoder().decode(Reply.self,from:data)
        guard let answer = parsed.choices.first?.message.content, !answer.isEmpty else {
            throw NSError(domain:"OmniForge.Online",code:2,userInfo:[NSLocalizedDescriptionKey:"Server returned an empty response"])
        }
        return answer
    }
    private static let account = "omniforge-online-api-key"
    static func saveKey(_ value: String) {
        let base: [String:Any] = [kSecClass as String:kSecClassGenericPassword,
                                 kSecAttrService as String:"com.r347h4ck3r.omniforge",
                                 kSecAttrAccount as String:account]
        SecItemDelete(base as CFDictionary)
        if !value.isEmpty {
            var query = base
            query[kSecValueData as String] = Data(value.utf8)
            query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            SecItemAdd(query as CFDictionary,nil)
        }
    }
    static func readKey() -> String? {
        let q: [String:Any] = [kSecClass as String:kSecClassGenericPassword,
                              kSecAttrService as String:"com.r347h4ck3r.omniforge",
                              kSecAttrAccount as String:account,
                              kSecReturnData as String:true,
                              kSecMatchLimit as String:kSecMatchLimitOne]
        var value: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary,&value) == errSecSuccess,
              let data = value as? Data else { return nil }
        return String(data:data,encoding:.utf8)
    }
}
