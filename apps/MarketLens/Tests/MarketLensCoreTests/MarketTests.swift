import XCTest
@testable import MarketLensCore
final class MarketTests: XCTestCase {
    let now = Date(timeIntervalSince1970: 1_800_000_000)
    func market() throws -> Market {
        try JSONDecoder().decode(Market.self, from: Data(#"{"ticker":"KXBTC15M-TEST","title":"BTC?","status":"active","open_time":"2027-01-15T07:55:00Z","close_time":"2027-01-15T08:10:00Z","floor_strike":62521.73,"strike_type":"greater_or_equal","rules_primary":"simple average sixty seconds CF Benchmarks BRTI","rules_secondary":"rounded to nearest 2 decimal places","result":""}"#.utf8))
    }
    func testDecodeOfficialRulesTargetAndOpenWindow() throws {
        let m = try market()
        XCTAssertEqual(m.target, D("62521.73"))
        XCTAssertTrue(m.supportsProxy)
        XCTAssertTrue(m.isOpen(at: now))
        XCTAssertFalse(m.isOpen(at: m.closeTime))
        XCTAssertFalse(m.isOpen(at: m.openTime.addingTimeInterval(-1)))
    }
    func testMissingTargetDoesNotInventZero() throws {
        let m = try JSONDecoder().decode(Market.self, from: Data(#"{"ticker":"T","title":"?","status":"active","open_time":"2027-01-15T07:55:00Z","close_time":"2027-01-15T08:10:00Z"}"#.utf8))
        XCTAssertNil(m.target)
        XCTAssertFalse(m.supportsProxy)
    }
    func testDecodeFixedPointBook() throws {
        let book = try PublicAPI.decodeBook(Data(#"{"orderbook_fp":{"yes_dollars":[["0.4500","8.50"]],"no_dollars":[["0.4900","3.00"]]}}"#.utf8))
        XCTAssertEqual(book.ask(.yes)?.price, D("0.51"))
        XCTAssertEqual(book.ask(.yes)?.quantity, 3)
        XCTAssertThrowsError(try PublicAPI.decodeBook(Data(#"{"orderbook_fp":{"yes_dollars":[["bad","1"]],"no_dollars":[]}}"#.utf8)))
    }
    func testDecodeBothPublicCoinbaseCandleFormats() throws {
        let classic = try PublicAPI.decodeCandles(Data("[[1800000000,99,102,100,101,4]]".utf8))
        XCTAssertEqual(classic.first?.close, 101)
        let advanced = try PublicAPI.decodeCandles(Data(#"{"candles":[{"start":"1800000000","close":"101"}]}"#.utf8))
        XCTAssertEqual(advanced.first?.time, now)
        XCTAssertEqual(advanced.first?.close, 101)
        XCTAssertThrowsError(try PublicAPI.decodeCandles(Data(#"{"candles":[{"start":"bad","close":"101"}]}"#.utf8)))
    }
    func testRejectsTrailingGarbageInFixedPointDecimal() {
        XCTAssertThrowsError(try PublicAPI.decodeBook(Data(#"{"orderbook_fp":{"yes_dollars":[["0.49garbage","1"]],"no_dollars":[]}}"#.utf8)))
        XCTAssertThrowsError(try PublicAPI.decodeBook(Data(#"{"orderbook_fp":{"yes_dollars":[["0.49","1e2"]],"no_dollars":[]}}"#.utf8)))
    }
    func testSnapshotGateRejectsStaleClosedAndClockSkew() throws {
        let m = try market()
        XCTAssertNil(Snapshot.blockingReason(market: m, receivedAt: now, serverTime: now, latency: 1, now: now))
        XCTAssertNotNil(Snapshot.blockingReason(market: m, receivedAt: now.addingTimeInterval(-31), serverTime: now, latency: 1, now: now))
        XCTAssertNotNil(Snapshot.blockingReason(market: m, receivedAt: now, serverTime: now.addingTimeInterval(-90), latency: 1, now: now))
        XCTAssertNotNil(Snapshot.blockingReason(market: m, receivedAt: now, serverTime: now, latency: 20, now: now))
        XCTAssertNotNil(Snapshot.blockingReason(market: m, receivedAt: m.closeTime, serverTime: m.closeTime, latency: 1, now: m.closeTime))
    }
}
