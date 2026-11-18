import XCTest
@testable import MarketLensCore
final class CoreTests: XCTestCase {
    func testComplementAskAndDepth() throws {
        let book = try OrderBook(yes: [Level(price: D("0.45"), quantity: D("8"))], no: [Level(price: D("0.49"), quantity: D("3"))])
        XCTAssertEqual(book.ask(.yes)?.price, D("0.51"))
        XCTAssertEqual(book.ask(.yes)?.quantity, D("3"))
        XCTAssertEqual(book.ask(.no)?.price, D("0.55"))
    }
    func testRejectCrossedBookAndInvalidLevel() {
        XCTAssertThrowsError(try OrderBook(yes: [.init(price: D("0.7"), quantity: 1)], no: [.init(price: D("0.4"), quantity: 1)]))
        XCTAssertThrowsError(try OrderBook(yes: [.init(price: -1, quantity: 1)], no: []))
        XCTAssertNil(try OrderBook(yes: [], no: []).ask(.yes))
    }
    func testDecimalFeeRoundingAndBreakEven() throws {
        let cost = try Cost.estimate(price: D("0.51"), contracts: 1)
        XCTAssertEqual(cost.total, D("0.5275"))
        XCTAssertEqual(cost.fee, D("0.0175"))
        XCTAssertEqual(cost.breakEven, D("0.5275"))
        XCTAssertEqual(try cost.expectedProfit(probability: D("0.5")), D("-0.0275"))
        XCTAssertEqual(try Cost.estimate(price: D("0.5"), contracts: 2).total, D("1.035"))
    }
    func testRejectInvalidEconomicsInputs() {
        for p in [D("-0.1"), 0, 1, D("1.1")] { XCTAssertThrowsError(try Cost.estimate(price: p, contracts: 1)) }
        XCTAssertThrowsError(try Cost.estimate(price: D("0.5"), contracts: 0))
        XCTAssertThrowsError(try Cost.estimate(price: D("0.5"), contracts: 1, multiplier: -1))
    }
}
func D(_ string: String) -> Decimal { Decimal(string: string, locale: Locale(identifier: "en_US_POSIX"))! }
