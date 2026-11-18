import Foundation
#if canImport(SwiftUI)
import Observation
#endif

#if canImport(SwiftUI)
@Observable
#endif
@MainActor public final class ResearchMonitor {
    public private(set) var snapshot: Snapshot?
    public private(set) var error: String?
    public private(set) var storageError: String?
    public private(set) var isRefreshing = false
    public private(set) var status = "Ready to check the current window."
    public private(set) var journal = Journal()
    public private(set) var lastAttempt: Date?
    public private(set) var settlementMessage: String?
    private let api: PublicAPI
    private let storage: URL?
    private var lastSettlementCheck: Date?
    public init(api: PublicAPI = PublicAPI(), storage: URL? = nil) {
        self.api = api; self.storage = storage
        if let storage {
            do { journal = try Journal.load(from: storage) }
            catch { storageError = "Could not read paper journal. Existing file preserved; adding entries is disabled. " + error.localizedDescription }
        }
    }
    public func refresh() async {
        guard !isRefreshing else { return }
        isRefreshing = true; lastAttempt = Date(); error = nil
        defer { isRefreshing = false }
        do {
            let markets = try await api.currentMarkets()
            try Task.checkCancellation()
            guard let market = markets.first(where: { $0.isOpen(at: Date()) }) else {
                snapshot = nil
                status = "No open BTC 15-minute window. Retrying while this screen is active."
                await refreshSettlements()
                return
            }
            let fresh = try await api.snapshot(market: market)
            try Task.checkCancellation()
            snapshot = fresh
            status = fresh.blockingReason(at: Date()) ?? "Public data received. REST quotes are not guaranteed executable."
            await refreshSettlements()
        } catch is CancellationError {
            snapshot = nil; status = "Foreground monitoring paused."
        } catch {
            snapshot = nil
            self.error = error.localizedDescription
            status = "Data unavailable. No estimate or paper entry until refresh succeeds."
        }
    }
    public func record(side: Side, contracts: Int, now: Date = Date()) throws {
        guard storageError == nil, let snapshot else { throw LensError.missingData }
        _ = try snapshot.cost(side: side, contracts: contracts, now: now)
        guard let ask = snapshot.book.ask(side), let multiplier = snapshot.feeMultiplier else { throw LensError.missingData }
        let midpoint = snapshot.book.bid(.yes).flatMap { bid in snapshot.book.ask(.yes).map { (bid.price + $0.price) / 2 } }
        let entry = try PaperEntry(ticker: snapshot.market.ticker, side: side, contracts: contracts, price: ask.price, multiplier: multiplier, probability: snapshot.forecast.proxyProbability, marketProbability: midpoint.map { NSDecimalNumber(decimal: $0).doubleValue }, createdAt: now, rules: snapshot.market.rules + "\n" + snapshot.market.secondaryRules, target: snapshot.market.target)
        var proposed = journal
        try proposed.add(entry)
        if let storage { try proposed.save(to: storage) }
        journal = proposed
    }
    public func refreshSettlements(force: Bool = false) async {
        guard storageError == nil, force || lastSettlementCheck.map({ Date().timeIntervalSince($0) > 60 }) != false else { return }
        lastSettlementCheck = Date()
        let tickers = Array(Set(journal.entries.filter { $0.result == nil }.map(\.ticker))).sorted().prefix(20)
        guard !tickers.isEmpty else { return }
        var proposed = journal
        var failed = 0
        for ticker in tickers {
            do {
                let official = try await api.market(ticker: ticker)
                try Task.checkCancellation()
                try proposed.settle(ticker: ticker, result: official.result, status: official.status)
            } catch { failed += 1 }
        }
        do {
            if let storage { try proposed.save(to: storage) }
            journal = proposed
            settlementMessage = failed == 0 ? "Official outcomes checked at \(Date().formatted(date: .omitted, time: .standard)). Unresolved entries remain pending." : "\(failed) official outcome checks failed. Existing results preserved."
        } catch { settlementMessage = "Could not save outcomes. Previous journal preserved: " + error.localizedDescription }
    }
}
