# Market Lens Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans task-by-task. Steps use checkbox syntax.

**Goal:** Native read-only live Kalshi BTC research app with honest probabilities and paper evaluation.
**Architecture:** Testable Foundation Swift package; thin SwiftUI scene; URLSession public clients; atomic local JSON journal.
**Tech Stack:** Swift 6, SwiftUI, Foundation, XcodeGen, iOS 26; no package dependencies.
**Spec:** ../../design.md

## Global Constraints
- iOS 26+, no orders/auth/paid billing; separate project and identity.
- Forecast is never independently validated in v1; no favorable-edge alerts.
- $25 maximum aggregate open hypothetical loss including fees, one-contract default.
- Refresh foreground only, explicit stale/closed/error states.
- Coordinate public release/catalog edits with root.

## Review Focus
- Crossed/empty books and missing fields must not become usable prices (task 1).
- Missing candle intervals or incomplete buckets must suppress baseline (task 2).
- Delayed response and window rollover must invalidate old signal (task 3).
- Duplicate outcomes and storage failure must not corrupt journal (task 4).
- Artifact metadata mismatch must fail release verification (task 5).

## Task 1: Quotes and economics
Files: Sources/MarketLensCore/Market.swift, Economics.swift; Tests/MarketLensCoreTests/CoreTests.swift.
Interfaces: Market decode; OrderBook.ask(side); Cost.estimate(price:contracts:multiplier:); available risk in journal.
- [ ] Add failing tests: bids-only complement, invalid/crossed book, Decimal51c one-contract total0.5275, invalid price/quantity, cap includes fees.
- [ ] Run swift test and record red.
- [ ] Implement minimal decoder and validated Decimal math.
- [ ] Run whole swift test suite; commit.

## Task 2: Independent research
Files: Forecast.swift, ForecastTests.swift.
Interface: Forecast.evaluate(candles:target:close:now:receivedAt:rulesSupported:) -> evaluation with optional proxy probability and reasons; reliable always false.
- [ ] Fail tests: flat volatility, missing interval, stale feed, final60s, insufficient candles, symmetric target returns approx0.5; odds never an input.
- [ ] Implement completed-minute-only baseline and clear unvalidated metadata.
- [ ] Run whole suite; commit.

## Task 3: Public monitoring and native UI
Files: PublicAPI.swift, Monitor.swift, App/MarketLensApp.swift; API/monitor tests.
Interfaces: fetch markets/book/candles with injected transport; refresh stores atomic per-market snapshot and invalidates on failure.
- [ ] Fail tests decoding fixture and stale/closed snapshot quality; request paths restricted GET public hosts.
- [ ] Implement async clients, explicit receive timestamps, 15s foreground loop, cards/tabs with accessible labels, empty/error states and source links.
- [ ] Run suite; macOS CI later runs native compile.

## Task 4: Paper journal and calibration
Files: Journal.swift; JournalTests.swift; paper tab.
Interfaces: add snapshot rejects over cap/duplicate, apply official result exact ticker, save atomic JSON, calibration Brier on resolved proxy estimates.
- [ ] Fail tests overspend/cross-ticker settlement/unresolved exclusion/roundtrip.
- [ ] Implement real local storage and official polling; no automatic bets.
- [ ] Run whole suite; commit.

## Task 5: Reproducible unsigned build
Files: project.yml, Info.plist, icon, build workflow, scripts/verify_ipa.py + tests, README.
- [ ] Test bad/missing metadata and valid synthetic artifact validator before implementation.
- [ ] Native simulator test + unsigned iphoneos build; package and verify size/hash/identity.
- [ ] Fresh review; fix regressions with red-green; report pass/fail/not-run distinctly.
- [ ] Only after parent coordination, durable public release and Strata registry addition.
