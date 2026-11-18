# Market Lens 0.1.0
Native SwiftUI iPhone research app (iOS26+), read-only public Kalshi BTC15m data and independent Coinbase candle baseline. No accounts, keys, trades, analytics, paid APIs, or guaranteed-profit claims.

## Status
Core tests are executable with Swift6.0+. Native Xcode build, simulator, signing and physical installation are separate verification stages. An unsigned IPA is not directly installable without a compatible signing/sideload workflow. No public release/catalog entry should be created until native build evidence is reviewed.

## Run
- `swift test` runs core tests.
- `python3 -m unittest discover -s scripts -p 'test_*.py' -v` tests package verification.
- On macOS with Xcode26 and XcodeGen: `xcodegen generate`, open `MarketLens.xcodeproj`.
- CI builds ARM64 unsigned Release, runs native UI smoke tests, produces IPA, SHA256SUMS, verified-ipa.json. No CI publication or catalog writes.

## What is real and what is not
Public markets, books, official rules, fee multipliers, Coinbase candles, local paper journal and official settlement checks are functional code. Foreground checks occur every15s; suspended iOS apps do not monitor continuously. REST receive timestamps are not quote timestamps. Empty, crossed, stale, unknown and closed states fail closed.

The independent probability shown, when inputs pass quality checks, is an **unvalidated zero-log-drift Coinbase endpoint proxy**. It is not the exact BRTI60s settlement average, not a trained model, not a confidence bound, and not evidence of a favorable edge. No favorable alert is enabled. Model validation requires chronological independent holdouts, no leakage, real execution costs and prospective evaluation. Local paper Brier scores are descriptive, not validation.

Default hypothetical size is one contract. Maximum aggregate open risk is $25 including fees, reduced by realized losses and never expanded by wins. This is only a local paper limit, not an account safeguard. Fee estimates use Decimal and the July7 2026 published quadratic taker formula. No maker fill assumptions.

Official sources: https://docs.kalshi.com/api-reference/market/get-market ; https://kalshi.com/docs/kalshi-fee-schedule.pdf ; https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles
