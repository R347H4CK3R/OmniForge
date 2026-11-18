// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "MarketLensCore", platforms: [.iOS("26.0"), .macOS(.v15)], products: [.library(name: "MarketLensCore", targets: ["MarketLensCore"])], targets: [.target(name: "MarketLensCore"), .testTarget(name: "MarketLensCoreTests", dependencies: ["MarketLensCore"])])
