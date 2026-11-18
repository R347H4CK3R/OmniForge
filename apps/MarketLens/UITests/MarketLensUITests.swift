import XCTest
final class MarketLensUITests: XCTestCase {
    func testReadOnlyDashboardAndMethodNavigation() {
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.staticTexts["Evidence before instinct."].waitForExistence(timeout: 10))
        app.tabBars.buttons["Method"].tap()
        XCTAssertTrue(app.navigationBars["Method & limits"].waitForExistence(timeout: 3))
        app.tabBars.buttons["Paper"].tap()
        XCTAssertTrue(app.navigationBars["Paper journal"].waitForExistence(timeout: 3))
        app.tabBars.buttons["Live"].tap()
        XCTAssertTrue(app.staticTexts["Evidence before instinct."].exists)
        let attachment = XCTAttachment(screenshot: app.screenshot()); attachment.lifetime = .keepAlways; add(attachment)
    }
}
