import Foundation

/// Opt-in network retrieval. This is not a general web-search engine.
enum ExternalToolRuntime {
    static func fetchPage(_ address: String) async throws -> String {
        guard let url=URL(string:address), url.scheme=="https",
              url.user==nil, url.password==nil, let host=url.host,
              !host.isEmpty else { throw URLError(.badURL) }
        // Block common local-only endpoints to reduce accidental private-network access.
        let h=host.lowercased()
        guard h != "localhost", h != "127.0.0.1", h != "::1",
              !h.hasSuffix(".local"), !h.hasSuffix(".internal") else { throw URLError(.unsupportedURL) }
        var request=URLRequest(url:url)
        request.timeoutInterval=20
        request.setValue("text/html,text/plain,application/json",forHTTPHeaderField:"Accept")
        let (data,response)=try await URLSession.shared.data(for:request)
        guard let http=response as? HTTPURLResponse,(200...299).contains(http.statusCode),
              data.count<=1_000_000 else { throw URLError(.badServerResponse) }
        guard let mime=http.mimeType,["text/html","text/plain","application/json"].contains(mime) else {
            throw URLError(.cannotDecodeContentData)
        }
        var output=String(decoding:data,as:UTF8.self)
        if mime=="text/html" {
            output=output.replacingOccurrences(of:"(?is)<script\\b[^>]*>.*?</script>|<style\\b[^>]*>.*?</style>",with:" ",options:.regularExpression)
            output=output.replacingOccurrences(of:"<[^>]+>",with:" ",options:.regularExpression)
        }
        return "Retrieved from "+url.absoluteString+"\n"+String(output.prefix(16000))
    }
}
