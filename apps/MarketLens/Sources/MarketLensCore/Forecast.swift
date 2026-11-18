import Foundation

public struct Candle: Codable, Sendable {
    public let time: Date
    public let close: Double
    public init(time: Date, close: Double) { self.time = time; self.close = close }
}
public struct Forecast: Codable, Sendable {
    public let proxyProbability: Double?
    public let reason: String
    public let evidenceTime: Date?
    public let sigma: Double?
    public let validUntil: Date?
    public func probability(at now: Date) -> Double? {
        guard let validUntil, now < validUntil else { return nil }
        return proxyProbability
    }
    public var reliable: Bool { false }
    public var canRecommend: Bool { false }
    public static let modelVersion = "coinbase-endpoint-proxy-v1"
    public static let limitation = "Unvalidated Coinbase endpoint proxy, not the official BRTI 60-second settlement average. No measured probability uncertainty or proven advantage."
    public static func unavailable(_ reason: String) -> Forecast { Forecast(proxyProbability: nil, reason: reason, evidenceTime: nil, sigma: nil, validUntil: nil) }
    public static func evaluate(candles: [Candle], target: Double?, close: Date, now: Date, receivedAt: Date, rulesSupported: Bool) -> Forecast {
        guard rulesSupported else { return .unavailable("Official settlement rules not recognized.") }
        guard let target, target.isFinite, target > 0 else { return .unavailable("Official target unavailable.") }
        let remaining = close.timeIntervalSince(now)
        guard remaining > 60, remaining <= 900 else { return .unavailable("Outside the eligible window or in its final 60 seconds.") }
        guard now.timeIntervalSince(receivedAt) >= -5, now.timeIntervalSince(receivedAt) <= 30 else { return .unavailable("Independent feed response is stale or clock differs.") }
        let complete = candles.filter { $0.time.addingTimeInterval(60) <= now }.sorted { $0.time < $1.time }
        guard complete.count >= 61 else { return .unavailable("Need 61 complete consecutive one-minute candles.") }
        let sample = Array(complete.suffix(61))
        guard let latest = sample.last, now.timeIntervalSince(latest.time.addingTimeInterval(60)) < 90,
              sample.allSatisfy({ $0.close.isFinite && $0.close > 0 }),
              zip(sample, sample.dropFirst()).allSatisfy({ abs($1.time.timeIntervalSince($0.time) - 60) < 0.01 }) else {
            return .unavailable("Missing, stale or invalid independent candles.")
        }
        let returns = zip(sample, sample.dropFirst()).map { log($1.close / $0.close) }
        let sigma = sqrt(returns.reduce(0) { $0 + $1 * $1 } / Double(returns.count))
        guard sigma.isFinite, sigma > 0 else { return .unavailable("Volatility cannot be estimated.") }
        // Last complete candle close is the independent observation, not Kalshi odds.
        let horizon = close.timeIntervalSince(latest.time.addingTimeInterval(60)) / 60
        let z = log(latest.close / target) / (sigma * sqrt(horizon))
        let p = 0.5 * (1 + erf(z / sqrt(2)))
        guard p.isFinite, p > 0.001, p < 0.999 else { return .unavailable("Proxy is outside the stable reporting range; uncertainty is unmeasured.") }
        return Forecast(proxyProbability: min(1, max(0, p)), reason: limitation, evidenceTime: latest.time.addingTimeInterval(60), sigma: sigma, validUntil: min(close.addingTimeInterval(-60), receivedAt.addingTimeInterval(30), latest.time.addingTimeInterval(150)))
    }
}
