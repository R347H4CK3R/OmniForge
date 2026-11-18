import XCTest
@testable import MarketLensCore
final class ForecastTests: XCTestCase {
    let now = Date(timeIntervalSince1970: 1_800_000_000)
    func candles(flat: Bool = false) -> [Candle] {
        (1...61).reversed().map { Candle(time: now.addingTimeInterval(Double(-$0 * 60)), close: flat ? 100 : ($0 % 2 == 0 ? 100.1 : 100)) }
    }
    func testIndependentSymmetricBaselineNeverValidated() {
        let r = Forecast.evaluate(candles: candles(), target: 100, close: now.addingTimeInterval(300), now: now, receivedAt: now, rulesSupported: true)
        XCTAssertEqual(r.proxyProbability ?? -1, 0.5, accuracy: 0.001)
        XCTAssertFalse(r.reliable)
        XCTAssertFalse(r.canRecommend)
    }
    func testMissingIntervalsFlatVolatilityStaleAndFinalMinuteSuppress() {
        var missing = candles(); missing.remove(at: 4)
        for data in [missing, candles(flat: true), Array(candles().prefix(20))] {
            XCTAssertNil(Forecast.evaluate(candles: data, target: 100, close: now.addingTimeInterval(300), now: now, receivedAt: now, rulesSupported: true).proxyProbability)
        }
        XCTAssertNil(Forecast.evaluate(candles: candles(), target: 100, close: now.addingTimeInterval(60), now: now, receivedAt: now, rulesSupported: true).proxyProbability)
        XCTAssertNil(Forecast.evaluate(candles: candles(), target: 100, close: now.addingTimeInterval(300), now: now, receivedAt: now.addingTimeInterval(-31), rulesSupported: true).proxyProbability)
        XCTAssertNil(Forecast.evaluate(candles: candles(), target: 100, close: now.addingTimeInterval(300), now: now, receivedAt: now, rulesSupported: false).proxyProbability)
    }
    func testExtremeProxyDoesNotImplyCertainty() {
        let r = Forecast.evaluate(candles: candles(), target: 0.01, close: now.addingTimeInterval(300), now: now, receivedAt: now, rulesSupported: true)
        XCTAssertNil(r.proxyProbability)
    }
    func testForecastExpiresAtFinalMinuteWithoutRefresh() {
        let r = Forecast.evaluate(candles: candles(), target: 100, close: now.addingTimeInterval(65), now: now, receivedAt: now, rulesSupported: true)
        XCTAssertNotNil(r.probability(at: now))
        XCTAssertNil(r.probability(at: now.addingTimeInterval(5)))
        XCTAssertNil(r.probability(at: now.addingTimeInterval(31)))
    }
    func testIncompleteBucketIgnored() {
        let data = candles() + [Candle(time: now, close: 999_999)]
        let r = Forecast.evaluate(candles: data, target: 100, close: now.addingTimeInterval(300), now: now, receivedAt: now, rulesSupported: true)
        XCTAssertEqual(r.proxyProbability ?? -1, 0.5, accuracy: 0.001)
    }
}
