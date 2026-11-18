import Foundation

public enum Side: String, Codable, Sendable, CaseIterable { case yes, no }
public enum LensError: Error, LocalizedError {
    case invalidInput, crossedBook, stale, closed, missingData, overBudget, duplicate, mismatchedOutcome, unsupportedFees
    public var errorDescription: String? {
        switch self {
        case .invalidInput: "Invalid price, quantity or probability."
        case .crossedBook: "Inconsistent order book. Refresh required."
        case .stale: "Evidence is stale. Refresh required."
        case .closed: "This window is not open."
        case .missingData: "Required evidence is unavailable."
        case .overBudget: "This exceeds the $25 open paper-loss cap, including estimated fees."
        case .duplicate: "This market and side are already in your paper journal."
        case .mismatchedOutcome: "Outcome does not match the recorded market."
        case .unsupportedFees: "This fee schedule is not supported."
        }
    }
}
public struct Level: Codable, Equatable, Sendable {
    public let price: Decimal
    public let quantity: Decimal
    public init(price: Decimal, quantity: Decimal) { self.price = price; self.quantity = quantity }
}
public struct OrderBook: Sendable {
    public let yes: [Level]
    public let no: [Level]
    public init(yes: [Level], no: [Level]) throws {
        guard (yes + no).allSatisfy({ !$0.price.isNaN && !$0.quantity.isNaN && $0.price > 0 && $0.price < 1 && $0.quantity > 0 }) else { throw LensError.invalidInput }
        self.yes = yes.sorted { $0.price > $1.price }
        self.no = no.sorted { $0.price > $1.price }
        if let y = self.yes.first, let n = self.no.first, y.price + n.price > 1 { throw LensError.crossedBook }
    }
    public func bid(_ side: Side) -> Level? { (side == .yes ? yes : no).first }
    public func ask(_ side: Side) -> Level? {
        guard let opposite = bid(side == .yes ? .no : .yes) else { return nil }
        return Level(price: 1 - opposite.price, quantity: opposite.quantity)
    }
}
public struct Cost: Codable, Sendable {
    public let contracts: Int
    public let total: Decimal
    public let fee: Decimal
    public var breakEven: Decimal { total / Decimal(contracts) }
    public var maximumProfit: Decimal { Decimal(contracts) - total }
    public static func estimate(price: Decimal, contracts: Int, multiplier: Decimal = 1) throws -> Cost {
        guard !price.isNaN, !multiplier.isNaN, price > 0, price < 1, contracts > 0, contracts <= 10_000, multiplier >= 0, multiplier <= 100 else { throw LensError.invalidInput }
        let principal = Decimal(contracts) * price
        let rawFee = multiplier * Decimal(string: "0.07")! * Decimal(contracts) * price * (1 - price)
        var rawTotal = principal + rawFee
        var rounded = Decimal()
        // Official July 7 2026 schedule rounds fee + position cost upward to 0.0001 USD.
        NSDecimalRound(&rounded, &rawTotal, 4, .up)
        return Cost(contracts: contracts, total: rounded, fee: rounded - principal)
    }
    public func expectedProfit(probability: Decimal) throws -> Decimal {
        guard !probability.isNaN, probability >= 0, probability <= 1 else { throw LensError.invalidInput }
        return Decimal(contracts) * probability - total
    }
}
