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
