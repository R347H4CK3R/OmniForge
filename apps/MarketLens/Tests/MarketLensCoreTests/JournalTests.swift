import XCTest
@testable import MarketLensCore
final class JournalTests: XCTestCase {
    func entry(_ ticker: String = "KXBTC15M-T1", contracts: Int = 1) throws -> PaperEntry {
        try PaperEntry(ticker: ticker, side: .yes, contracts: contracts, price: D("0.5"), multiplier: 1, probability: 0.8, marketProbability: 0.6, createdAt: Date(timeIntervalSince1970: 1_800_000_000), rules: "Official rules", target: 100)
    }
    func testBudgetIncludesFeesAndRejectsDuplicate() throws {
        var journal = Journal()
        try journal.add(entry(contracts: 48))
        XCTAssertEqual(journal.availableRisk, D("0.16"))
        XCTAssertThrowsError(try journal.add(entry("KXBTC15M-T2")))
        XCTAssertThrowsError(try journal.add(entry()))
        XCTAssertEqual(journal.entries.count, 1)
    }
    func testOfficialResultsOnlyExactTickerAndNoUnresolvedCalibration() throws {
        var journal = Journal(); try journal.add(entry())
        XCTAssertEqual(journal.calibration.count, 0)
        XCTAssertThrowsError(try journal.settle(ticker: "WRONG", result: "yes", status: "settled"))
        try journal.settle(ticker: "KXBTC15M-T1", result: "yes", status: "active")
        XCTAssertEqual(journal.calibration.count, 0)
        try journal.settle(ticker: "KXBTC15M-T1", result: "yes", status: "settled")
        XCTAssertEqual(journal.calibration.count, 1)
        XCTAssertEqual(journal.calibration.brier ?? -1, 0.04, accuracy: 0.000001)
        XCTAssertEqual(journal.calibration.marketBrier ?? -1, 0.16, accuracy: 0.000001)
        XCTAssertEqual(journal.realizedProfit, D("0.4825"))
        XCTAssertEqual(journal.availableRisk, 25)
    }
    func testLossConsumesBudgetAndPersistenceRoundtrip() throws {
        var journal = Journal(); try journal.add(entry())
        try journal.settle(ticker: "KXBTC15M-T1", result: "no", status: "finalized")
        XCTAssertEqual(journal.availableRisk, D("24.4825"))
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        let url = dir.appendingPathComponent("paper.json")
        try journal.save(to: url)
        let restored = try Journal.load(from: url)
        XCTAssertEqual(restored.entries.count, 1)
        XCTAssertEqual(restored.realizedProfit, D("-0.5175"))
    }
}
