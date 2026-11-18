import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

public struct HTTPResult: Sendable {
    public let data: Data
    public let receivedAt: Date
    public let serverTime: Date?
    public let latency: TimeInterval
    public init(data: Data, receivedAt: Date, serverTime: Date?, latency: TimeInterval) { self.data=data; self.receivedAt=receivedAt; self.serverTime=serverTime; self.latency=latency }
}
public struct PublicAPI: Sendable {
    public typealias Transport = @Sendable (URL) async throws -> HTTPResult
    private let transport: Transport
    public init(transport: @escaping Transport = PublicAPI.get) { self.transport = transport }
    public static func get(_ url: URL) async throws -> HTTPResult {
        guard url.scheme == "https", ["external-api.kalshi.com", "api.exchange.coinbase.com"].contains(url.host ?? "") else { throw LensError.invalidInput }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 12)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let start = Date()
        let (data, response) = try await URLSession.shared.data(for: request)
        let received = Date()
        guard let http = response as? HTTPURLResponse, http.statusCode == 200, data.count < 4_000_000 else { throw LensError.missingData }
        let formatter = DateFormatter(); formatter.locale = Locale(identifier: "en_US_POSIX"); formatter.timeZone = TimeZone(secondsFromGMT: 0); formatter.dateFormat = "EEE',' dd MMM yyyy HH':'mm':'ss z"
        let serverTime = http.value(forHTTPHeaderField: "Date").flatMap(formatter.date(from:))
        return HTTPResult(data: data, receivedAt: received, serverTime: serverTime, latency: received.timeIntervalSince(start))
    }
    private static let base = "https://external-api.kalshi.com/trade-api/v2"
    public func currentMarkets() async throws -> [Market] {
        let r = try await transport(URL(string: Self.base + "/markets?series_ticker=KXBTC15M&status=open&limit=50")!)
        struct Envelope: Decodable { let markets: [Market] }
        return try JSONDecoder().decode(Envelope.self, from: r.data).markets.sorted { $0.closeTime < $1.closeTime }
    }
    public func market(ticker: String) async throws -> Market {
        guard !ticker.isEmpty, ticker.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-") }) else { throw LensError.invalidInput }
        struct Envelope: Decodable { let market: Market }
        let response = try await transport(URL(string: Self.base + "/markets/" + ticker)!)
        let market = try JSONDecoder().decode(Envelope.self, from: response.data).market
        guard market.ticker == ticker else { throw LensError.mismatchedOutcome }
        return market
    }
    public static func decodeBook(_ data: Data) throws -> OrderBook {
        struct Body: Decodable { let yes_dollars: [[String]]?; let no_dollars: [[String]]? }
        struct Envelope: Decodable { let orderbook_fp: Body }
        let body = try JSONDecoder().decode(Envelope.self, from: data).orderbook_fp
        func parse(_ rows: [[String]]?) throws -> [Level] {
            try (rows ?? []).map { row in
                guard row.count == 2, let price = Decimal(string: row[0], locale: Locale(identifier: "en_US_POSIX")), let quantity = Decimal(string: row[1], locale: Locale(identifier: "en_US_POSIX")) else { throw LensError.invalidInput }
                return Level(price: price, quantity: quantity)
            }
        }
        return try OrderBook(yes: parse(body.yes_dollars), no: parse(body.no_dollars))
    }
    public func snapshot(market: Market) async throws -> Snapshot {
        guard market.ticker.hasPrefix("KXBTC15M-"), market.ticker.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-") }) else { throw LensError.invalidInput }
        async let rawBook = transport(URL(string: Self.base + "/markets/" + market.ticker + "/orderbook?depth=10")!)
        async let rawCandles = try? transport(URL(string: "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60")!)
        async let rawSeries = try? transport(URL(string: Self.base + "/series/KXBTC15M")!)
        let (bookResponse, candleResponse, seriesResponse) = try await (rawBook, rawCandles, rawSeries)
        let book = try Self.decodeBook(bookResponse.data)
        let now = Date()
        var forecast = Forecast.unavailable("Independent feed unavailable.")
        if let response = candleResponse, let rows = try? JSONDecoder().decode([[Double]].self, from: response.data), rows.allSatisfy({ $0.count >= 6 }) {
            let candles = rows.map { Candle(time: Date(timeIntervalSince1970: $0[0]), close: $0[4]) }
            forecast = Forecast.evaluate(candles: candles, target: market.target.map { NSDecimalNumber(decimal: $0).doubleValue }, close: market.closeTime, now: now, receivedAt: response.receivedAt, rulesSupported: market.supportsProxy)
        }
        struct Series: Decodable { let ticker: String; let fee_type: String; let fee_multiplier: Decimal }
        struct SeriesEnvelope: Decodable { let series: Series }
        var multiplier: Decimal?
        if let response = seriesResponse, let series = try? JSONDecoder().decode(SeriesEnvelope.self, from: response.data).series, series.ticker == "KXBTC15M", series.fee_type == "quadratic", series.fee_multiplier >= 0, series.fee_multiplier <= 100 { multiplier = series.fee_multiplier }
        return Snapshot(market: market, book: book, receivedAt: bookResponse.receivedAt, serverTime: bookResponse.serverTime, latency: bookResponse.latency, forecast: forecast, feeMultiplier: multiplier, feeReceivedAt: seriesResponse?.receivedAt)
    }
}
