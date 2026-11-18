import XCTest
@testable import MarketLensCore
@MainActor final class MonitorTests: XCTestCase {
    func testFailureClearsSnapshotAndReportsError() async {
        let api = PublicAPI(transport: { _ in throw LensError.missingData })
        let monitor = ResearchMonitor(api: api)
        await monitor.refresh()
        XCTAssertNil(monitor.snapshot)
        XCTAssertNotNil(monitor.error)
        XCTAssertFalse(monitor.isRefreshing)
    }
    func testMalformedJournalIsNotSilentlyOverwritten() throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try Data("not JSON".utf8).write(to: url)
        defer { try? FileManager.default.removeItem(at: url) }
        let monitor = ResearchMonitor(storage: url)
        XCTAssertNotNil(monitor.storageError)
        XCTAssertEqual(try String(contentsOf: url, encoding: .utf8), "not JSON")
    }
    func testNoActiveMarketHasHonestEmptyState() async {
        let api = PublicAPI(transport: { _ in HTTPResult(data: Data(#"{"markets":[]}"#.utf8), receivedAt: Date(), serverTime: Date(), latency: 0.1) })
        let monitor = ResearchMonitor(api: api)
        await monitor.refresh()
        XCTAssertNil(monitor.snapshot)
        XCTAssertEqual(monitor.status, "No open BTC 15-minute window. Retrying while this screen is active.")
    }
    func testInvalidTickerCannotConstructExternalPath() async {
        let api = PublicAPI(transport: { _ in XCTFail("Transport must not be called"); throw LensError.missingData })
        do { _ = try await api.market(ticker: "../private?token=x"); XCTFail("Expected rejection") } catch {}
    }
}

private actor SettlementGate {
    private var continuation: CheckedContinuation<Void, Never>?
    var waiting = false
    func wait() async { waiting = true; await withCheckedContinuation { continuation = $0 } }
    func release() { continuation?.resume(); continuation = nil }
}

extension MonitorTests {
    func testRecordingDuringSettlementDoesNotLoseEntry() async throws { try await settlementScenario(cancel: false) }
    func testCancelledSettlementDoesNotPersistResults() async throws { try await settlementScenario(cancel: true) }
    private func settlementScenario(cancel: Bool) async throws {
        let gate = SettlementGate()
        let now = Date()
        let formatter = ISO8601DateFormatter()
        let open = formatter.string(from: now.addingTimeInterval(-300))
        let close = formatter.string(from: now.addingTimeInterval(300))
        let market = """
        {"ticker":"KXBTC15M-TEST","title":"BTC?","status":"active","open_time":"\(open)","close_time":"\(close)","floor_strike":100,"strike_type":"greater_or_equal","rules_primary":"sixty seconds BRTI","result":""}
        """
        let api = PublicAPI(transport: { url in
            let data: String
            if url.path.hasSuffix("/orderbook") { data = #"{"orderbook_fp":{"yes_dollars":[["0.49","10"]],"no_dollars":[["0.49","10"]]}}"# }
            else if url.path.contains("/series/") { data = #"{"series":{"ticker":"KXBTC15M","fee_type":"quadratic","fee_multiplier":1}}"# }
            else if url.path.hasSuffix("/candles") { data = "[]" }
            else if url.path.hasSuffix("/markets") { data = "{\"markets\":[\(market)]}" }
            else {
                await gate.wait()
                data = "{\"market\":\(market.replacingOccurrences(of: "\"active\"", with: "\"settled\"").replacingOccurrences(of: "\"result\":\"\"", with: "\"result\":\"yes\""))}"
            }
            return HTTPResult(data: Data(data.utf8), receivedAt: Date(), serverTime: Date(), latency: 0.1)
        })
        let monitor = ResearchMonitor(api: api)
        await monitor.refresh()
        try monitor.record(side: .yes, contracts: 1)
        let settlement = Task { await monitor.refreshSettlements(force: true) }
        while !(await gate.waiting) { await Task.yield() }
        try monitor.record(side: .no, contracts: 1)
        if cancel { settlement.cancel() }
        await gate.release()
        await settlement.value
        XCTAssertEqual(monitor.journal.entries.count, 2)
        XCTAssertEqual(monitor.journal.entries.filter { $0.result == "yes" }.count, cancel ? 0 : 2)
    }
}
