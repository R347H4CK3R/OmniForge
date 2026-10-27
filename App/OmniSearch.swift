import Foundation

/// Public web search against an explicitly configured SearXNG JSON endpoint.
/// Search needs an internet connection and an instance with JSON enabled.
enum OmniSearch {
    struct Result: Decodable {
        let title: String
        let url: String
        let content: String?
    }
    struct Response: Decodable { let results: [Result] }

    static func search(_ query: String) async throws -> String {
        let base = UserDefaults.standard.string(forKey: "searxngURL") ?? ""
        guard var url = URLComponents(string: base),
              url.scheme == "https", url.host != nil,
              url.user == nil, url.password == nil else {
            return "Web search not configured. Enter the HTTPS URL of a SearXNG instance with JSON responses enabled in Models."
        }
        url.path = url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/")) == "" ? "/search" : url.path
        url.queryItems = [URLQueryItem(name:"q",value:query),
                          URLQueryItem(name:"format",value:"json")]
        guard let address = url.url else { throw URLError(.badURL) }
        var request = URLRequest(url:address)
        request.timeoutInterval = 30
        request.setValue("application/json",forHTTPHeaderField:"Accept")
        let (data,response) = try await URLSession.shared.data(for:request)
        guard let status = response as? HTTPURLResponse, status.statusCode == 200,
              data.count < 2_000_000 else { throw URLError(.badServerResponse) }
        let parsed = try JSONDecoder().decode(Response.self,from:data)
        let rows = parsed.results.prefix(8).compactMap { hit -> String? in
            guard let link = URL(string:hit.url), ["https","http"].contains(link.scheme ?? "") else { return nil }
            return hit.title+"\n"+hit.url+"\n"+String((hit.content ?? "").prefix(500))
        }
        return rows.isEmpty ? "No search results." : rows.joined(separator:"\n\n")
    }
}
