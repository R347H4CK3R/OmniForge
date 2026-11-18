import Foundation

public enum Dates {
    public static func parse(_ value: String) -> Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: value) ?? ISO8601DateFormatter().date(from: value)
    }
}
public struct Market: Decodable, Sendable, Identifiable {
    public var id: String { ticker }
    public let ticker: String
    public let title: String
    public let status: String
    public let target: Decimal?
    public let openTime: Date
    public let closeTime: Date
    public let rules: String
    public let secondaryRules: String
    public let strikeType: String
    public let result: String
    enum CodingKeys: String, CodingKey {
        case ticker, title, status, result
        case target = "floor_strike", openTime = "open_time", closeTime = "close_time"
        case rules = "rules_primary", secondaryRules = "rules_secondary", strikeType = "strike_type"
    }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        ticker = try c.decode(String.self, forKey: .ticker)
        title = try c.decode(String.self, forKey: .title)
        status = try c.decode(String.self, forKey: .status)
        target = try c.decodeIfPresent(Decimal.self, forKey: .target)
        guard let open = Dates.parse(try c.decode(String.self, forKey: .openTime)), let close = Dates.parse(try c.decode(String.self, forKey: .closeTime)), close > open else { throw LensError.invalidInput }
        openTime = open; closeTime = close
        rules = try c.decodeIfPresent(String.self, forKey: .rules) ?? ""
        secondaryRules = try c.decodeIfPresent(String.self, forKey: .secondaryRules) ?? ""
        strikeType = try c.decodeIfPresent(String.self, forKey: .strikeType) ?? ""
        result = try c.decodeIfPresent(String.self, forKey: .result) ?? ""
    }
    public var supportsProxy: Bool {
        ticker.hasPrefix("KXBTC15M-") && strikeType == "greater_or_equal" && rules.contains("BRTI") && rules.lowercased().contains("sixty seconds") && target.map { $0 > 0 } == true
    }
    public func isOpen(at date: Date) -> Bool { (status == "active" || status == "open") && date >= openTime && date < closeTime }
}
public struct Snapshot: Sendable {
    public let market: Market
    public let book: OrderBook
    public let receivedAt: Date
    public let serverTime: Date?
    public let latency: TimeInterval
    public let forecast: Forecast
    public let feeMultiplier: Decimal?
    public let feeReceivedAt: Date?
    public static func blockingReason(market: Market, receivedAt: Date, serverTime: Date?, latency: TimeInterval, now: Date) -> String? {
        guard market.isOpen(at: now) else { return "Market is not open. Waiting for the next window." }
        guard now.timeIntervalSince(receivedAt) >= -5, now.timeIntervalSince(receivedAt) <= 30, latency <= 10, latency >= 0 else { return "Stale or delayed response. Refresh before evaluating." }
        guard let serverTime, abs(receivedAt.timeIntervalSince(serverTime)) <= 30 else { return "Server response time unavailable, stale, or clock mismatch." }
        return nil
    }
    public func blockingReason(at now: Date) -> String? { Self.blockingReason(market: market, receivedAt: receivedAt, serverTime: serverTime, latency: latency, now: now) }
    public func cost(side: Side, contracts: Int, now: Date) throws -> Cost {
        guard blockingReason(at: now) == nil else { throw LensError.stale }
        guard let multiplier = feeMultiplier, let feeReceivedAt, now.timeIntervalSince(feeReceivedAt) <= 300 else { throw LensError.unsupportedFees }
        guard let ask = book.ask(side), ask.quantity >= Decimal(contracts) else { throw LensError.missingData }
        return try Cost.estimate(price: ask.price, contracts: contracts, multiplier: multiplier)
    }
}
