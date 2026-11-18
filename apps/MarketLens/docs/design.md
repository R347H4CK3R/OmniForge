# Market Lens v1
Native SwiftUI research-only iPhone app, iOS 26+, standalone unsigned IPA intended for Strata. No authentication, orders, private keys, paid services or promises of profit.

## User-approved purpose
Live BTC 15-minute Kalshi market monitoring with independently sourced research, probability estimates only when justified, transparent hypothetical after-fee economics, and paper outcomes. Foreground automatic refresh 15 seconds after each completed check; no false claim of continuous iOS background service.

## Design
Core Swift package separates Kalshi API decoding, market/orderbook quality gates, Decimal cost calculator, independent Coinbase baseline, and a local paper journal. App displays quotes/depth, countdown, official target/rules, response receive times and latency, model assumptions and calibration status. API metadata update times are not quote timestamps. Fail closed on missing/stale/mismatched data, closed windows, sparse candles or unsupported settlement semantics.

No trained coefficients or validation records exist. A transparent zero-log-drift volatility baseline may be shown explicitly as an experimental endpoint proxy, not a reliable BRTI-average forecast. It never enables favorable-edge alerts. Missing/invalid evidence displays “No reliable estimate.” A 60-second final-window embargo blocks proxy forecasts. Odds and independent probabilities are separate.

Decimal hypothetical cost uses documented July 2026 standard taker coefficient 0.07, configurable multiplier, rounding total cost up to 0.0001 dollars. Fee schedule not verified for this series is prominently estimated. Default one contract; $25 is aggregate outstanding paper loss including fees, never a stake recommendation or account-wide protection. Paper entries persist locally, immutable prediction, official outcome fetched by exact ticker only; void/unknown separate. Calibration reports matched settled predictions only and never labels a model validated based on sample count alone.

## Verification/release
Unit tests on Swift core with fixtures, URLProtocol/request injection tests where feasible, iOS build and simulator tests on macOS Actions. IPA metadata, arm64, checksum and artifact verified. Public release and catalog mutation coordinated with root, never automatic as part of branch CI. Unsigned requires signing in compatible sideload installer; physical installation remains separate validation.
