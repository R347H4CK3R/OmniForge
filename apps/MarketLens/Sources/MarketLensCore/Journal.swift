import Foundation

public struct PaperEntry: Codable, Sendable, Identifiable {
    public let id: UUID
    public let ticker: String
    public let side: Side
    public let price: Decimal
    public let cost: Cost
    public let probability: Double?
    public let marketProbability: Double?
    public let modelVersion: String
    public let createdAt: Date
    public let rules: String
    public let target: Decimal?
    public fileprivate(set) var result: String?
    public fileprivate(set) var settledAt: Date?
    public init(ticker: String, side: Side, contracts: Int, price: Decimal, multiplier: Decimal, probability: Double?, marketProbability: Double?, createdAt: Date, rules: String, target: Decimal?) throws {
        guard ticker.hasPrefix("KXBTC15M-"), !rules.isEmpty, [probability, marketProbability].allSatisfy({ $0 == nil || ($0!.isFinite && (0...1).contains($0!)) }) else { throw LensError.invalidInput }
        id = UUID(); self.ticker = ticker; self.side = side; self.price = price
        cost = try Cost.estimate(price: price, contracts: contracts, multiplier: multiplier)
        self.probability = probability; self.marketProbability = marketProbability
        modelVersion = Forecast.modelVersion; self.createdAt = createdAt; self.rules = rules; self.target = target
    }
    public var profit: Decimal? {
        guard let result, result == "yes" || result == "no" else { return nil }
        return (result == side.rawValue ? Decimal(cost.contracts) : 0) - cost.total
    }
}
public struct Calibration: Sendable {
    public let count: Int
    public let brier: Double?
    public let marketBrier: Double?
}
public struct Journal: Codable, Sendable {
    public private(set) var entries: [PaperEntry] = []
    public init() {}
    public var realizedProfit: Decimal { entries.compactMap(\.profit).reduce(0, +) }
    public var openRisk: Decimal { entries.filter { $0.result == nil }.reduce(0) { $0 + $1.cost.total } }
    public var availableRisk: Decimal { max(0, min(25, 25 + realizedProfit) - openRisk) }
    public mutating func add(_ entry: PaperEntry) throws {
        guard !entries.contains(where: { $0.ticker == entry.ticker && $0.side == entry.side }) else { throw LensError.duplicate }
        guard entry.cost.total <= availableRisk else { throw LensError.overBudget }
        entries.append(entry)
    }
    public mutating func settle(ticker: String, result: String, status: String) throws {
        guard entries.contains(where: { $0.ticker == ticker }) else { throw LensError.mismatchedOutcome }
        guard ["settled", "finalized"].contains(status), ["yes", "no"].contains(result) else { return }
        for index in entries.indices where entries[index].ticker == ticker && entries[index].result == nil {
            entries[index].result = result; entries[index].settledAt = Date()
        }
    }
    public var calibration: Calibration {
        // One observation per market: multiple sides must not inflate validation sample count.
        var seen = Set<String>()
        let paired = entries.filter { entry in
            guard entry.profit != nil, entry.probability != nil, entry.marketProbability != nil, !seen.contains(entry.ticker) else { return false }
            seen.insert(entry.ticker); return true
        }
        guard !paired.isEmpty else { return Calibration(count: 0, brier: nil, marketBrier: nil) }
        let brier = paired.reduce(0.0) { sum, entry in let y = entry.result == "yes" ? 1.0 : 0.0; return sum + pow(entry.probability! - y, 2) } / Double(paired.count)
        let market = paired.reduce(0.0) { sum, entry in let y = entry.result == "yes" ? 1.0 : 0.0; return sum + pow(entry.marketProbability! - y, 2) } / Double(paired.count)
        return Calibration(count: paired.count, brier: brier, marketBrier: market)
    }
    public func save(to url: URL) throws {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(self).write(to: url, options: .atomic)
    }
    public static func load(from url: URL) throws -> Journal {
        guard FileManager.default.fileExists(atPath: url.path) else { return Journal() }
        return try JSONDecoder().decode(Journal.self, from: Data(contentsOf: url))
    }
}
