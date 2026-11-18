import SwiftUI
import MarketLensCore

@main
struct MarketLensApp: App {
    var body: some Scene { WindowGroup { Dashboard().preferredColorScheme(.dark) } }
}

struct Dashboard: View {
    @Environment(\.scenePhase) private var scenePhase
    @State private var monitor: ResearchMonitor
    @State private var side: Side = .yes
    @State private var contracts = 1
    @State private var notice: String?
    private let accent = Color(red: 0.34, green: 0.85, blue: 0.78)
    init() {
        let support = URL.applicationSupportDirectory.appendingPathComponent("MarketLens", isDirectory: true)
        try? FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
        _monitor = State(initialValue: ResearchMonitor(storage: support.appendingPathComponent("paper-journal-v1.json")))
    }
    var body: some View {
        TabView {
            NavigationStack {
                TimelineView(.periodic(from: .now, by: 1)) { context in
                    ScrollView {
                        VStack(alignment: .leading, spacing: 18) {
                            hero
                            if let snapshot = monitor.snapshot {
                                marketCard(snapshot, now: context.date)
                                researchCard(snapshot, now: context.date)
                                scenarioCard(snapshot, now: context.date)
                                rulesCard(snapshot)
                            } else {
                                panel {
                                    Label(monitor.isRefreshing ? "Checking public markets" : "Waiting for evidence", systemImage: "antenna.radiowaves.left.and.right")
                                        .font(.title3.bold())
                                    Text(monitor.status).foregroundStyle(.secondary)
                                    if let error = monitor.error { Text(error).font(.footnote).foregroundStyle(.orange) }
                                    Button("Refresh now") { Task { await monitor.refresh() } }.buttonStyle(.borderedProminent).disabled(monitor.isRefreshing)
                                }
                            }
                            Text("Read-only • No Kalshi account access • No orders")
                                .font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity)
                        }.padding()
                    }
                }
                .background(Color(red: 0.035, green: 0.055, blue: 0.085))
                .navigationTitle("Market Lens")
                .toolbar { ToolbarItem(placement: .topBarTrailing) {
                    Button { Task { await monitor.refresh() } } label: { Image(systemName: "arrow.clockwise") }.accessibilityLabel("Refresh markets").disabled(monitor.isRefreshing)
                } }
            }.tabItem { Label("Live", systemImage: "waveform.path.ecg") }
            NavigationStack { journalView.navigationTitle("Paper journal") }.tabItem { Label("Paper", systemImage: "book.closed") }
            NavigationStack { methodView.navigationTitle("Method & limits") }.tabItem { Label("Method", systemImage: "function") }
        }
        .tint(accent)
        .task(id: scenePhase) {
            guard scenePhase == .active else { return }
            while !Task.isCancelled {
                await monitor.refresh()
                do { try await Task.sleep(for: .seconds(15)) } catch { return }
            }
        }
        .task(id: scenePhase) {
            guard scenePhase == .active else { return }
            while !Task.isCancelled {
                await monitor.refreshSettlements()
                do { try await Task.sleep(for: .seconds(60)) } catch { return }
            }
        }
        .alert("Paper journal", isPresented: Binding(get: { notice != nil }, set: { if !$0 { notice = nil } })) { Button("OK") { notice = nil } } message: { Text(notice ?? "") }
    }
    private var hero: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Label("BTC · 15 MIN", systemImage: "bitcoinsign.circle").font(.caption.weight(.bold)).tracking(1.5)
                Spacer()
                Text(scenePhase == .active ? "FOREGROUND" : "PAUSED").font(.caption2.weight(.bold)).foregroundStyle(accent)
            }
            Text("Evidence before instinct.").font(.largeTitle.bold())
            Text("No verified edge. Research and paper scenarios only.").font(.subheadline).foregroundStyle(.secondary)
            Text("Refreshes 15 seconds after each check while open. Slow connections can delay data; background monitoring is not continuous.").font(.caption).foregroundStyle(.secondary)
        }
    }
    private func marketCard(_ s: Snapshot, now: Date) -> some View {
        panel {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 5) { Text(s.market.title).font(.title3.bold()); Text(s.market.ticker).font(.caption.monospaced()).foregroundStyle(.secondary) }
                Spacer()
                let remaining = max(0, Int(s.market.closeTime.timeIntervalSince(now)))
                Text(String(format: "%02d:%02d", remaining / 60, remaining % 60)).font(.title2.monospacedDigit().bold()).accessibilityLabel("Window closes in \(remaining) seconds")
            }
            Text("Official target  \(money(s.market.target))").font(.headline)
            HStack(spacing: 12) { quoteColumn(s, side: .yes); quoteColumn(s, side: .no) }
            Divider()
            if let reason = s.blockingReason(at: now) { Label(reason, systemImage: "exclamationmark.triangle").font(.footnote).foregroundStyle(.orange) }
            Text("Received \(s.receivedAt.formatted(date: .omitted, time: .standard)) · \(max(0, Int(now.timeIntervalSince(s.receivedAt))))s ago · \(s.latency, specifier: "%.1f")s request").font(.caption).foregroundStyle(.secondary)
            Text("Receive time is not the exchange quote-update time. Prices can change before execution.").font(.caption2).foregroundStyle(.secondary)
        }
    }
    private func quoteColumn(_ s: Snapshot, side: Side) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(side.rawValue.uppercased()).font(.caption.bold()).foregroundStyle(accent)
            Text(money(s.book.ask(side)?.price)).font(.title.bold().monospacedDigit())
            Text("Ask · bid \(money(s.book.bid(side)?.price))").font(.caption).foregroundStyle(.secondary)
            Text("Top ask size \(number(s.book.ask(side)?.quantity))").font(.caption2).foregroundStyle(.secondary)
        }.frame(maxWidth: .infinity, alignment: .leading).padding(12).background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 12))
    }
    private func researchCard(_ s: Snapshot, now: Date) -> some View {
        panel {
            Label("Independent research", systemImage: "sparkle.magnifyingglass").font(.headline)
            Text("No reliable win-probability estimate").font(.title3.bold())
            if s.blockingReason(at: now) == nil, let p = s.proxyProbability(at: now) {
                HStack { Text("Experimental endpoint proxy · YES"); Spacer(); Text(percent(p)).monospacedDigit().bold() }.font(.subheadline)
                Text(s.forecast.reason).font(.footnote).foregroundStyle(.orange)
                if let evidence = s.forecast.evidenceTime { Text("Last completed Coinbase candle: \(evidence.formatted(date: .omitted, time: .standard))").font(.caption).foregroundStyle(.secondary) }
            } else { Text(s.blockingReason(at: now) ?? s.forecast.reason).font(.footnote).foregroundStyle(.secondary) }
            if let bid = s.book.bid(.yes), let ask = s.book.ask(.yes) {
                Text("Market midpoint: \(percent(NSDecimalNumber(decimal: (bid.price + ask.price) / 2).doubleValue)) YES. This is a market price, not independent evidence.").font(.caption).foregroundStyle(.secondary)
            }
            Text("Uncertainty: not calibrated. Favorable-edge alerts disabled.").font(.caption.weight(.semibold)).foregroundStyle(.orange)
        }
    }
    private func scenarioCard(_ s: Snapshot, now: Date) -> some View {
        panel {
            Label("Hypothetical outcome", systemImage: "slider.horizontal.3").font(.headline)
            Picker("Contract side", selection: $side) { Text("YES").tag(Side.yes); Text("NO").tag(Side.no) }.pickerStyle(.segmented)
            Stepper("\(contracts) contract\(contracts == 1 ? "" : "s")", value: $contracts, in: 1...10)
            if let cost = try? s.cost(side: side, contracts: contracts, now: now) {
                valueRow("Maximum loss, including fees", money(cost.total))
                valueRow("Estimated taker fee", money(cost.fee))
                valueRow("Net profit if correct", money(cost.maximumProfit))
                valueRow("Break-even probability", percent(NSDecimalNumber(decimal: cost.breakEven).doubleValue))
                if let pYes = s.proxyProbability(at: now) {
                    let p = side == .yes ? pYes : 1 - pYes
                    let ev = try? cost.expectedProfit(probability: Decimal(p))
                    valueRow("Proxy settlement probability", percent(p))
                    valueRow("Proxy average profit/loss", money(ev))
                    Text("A correct settlement produces the displayed profit only if filled at the assumed price and fees. These are conditional model outputs, not a prediction that this bet will profit. No statistical confidence bound is available.").font(.caption).foregroundStyle(.orange)
                }
                Text("Fees estimated from the current series multiplier and published taker formula. Holding to settlement assumed; no fill/slippage guarantee.").font(.caption).foregroundStyle(.secondary)
                Button {
                    do { try monitor.record(side: side, contracts: contracts); notice = "Paper scenario saved locally. No trade was placed." }
                    catch { notice = error.localizedDescription }
                } label: { Label("Save paper scenario", systemImage: "plus.circle").frame(maxWidth: .infinity) }
                .buttonStyle(.borderedProminent).disabled(cost.total > monitor.journal.availableRisk || monitor.storageError != nil)
            } else {
                Text("Scenario unavailable: stale/closed market, unknown fee type, or insufficient visible depth.").font(.footnote).foregroundStyle(.orange)
            }
            Text("Paper risk remaining: \(money(monitor.journal.availableRisk)) of $25. This does not monitor or limit your real account.").font(.caption).foregroundStyle(.secondary)
            if let error = monitor.storageError { Text(error).font(.caption).foregroundStyle(.orange) }
        }
    }
    private func rulesCard(_ s: Snapshot) -> some View {
        panel {
            DisclosureGroup("Official settlement rules") {
                VStack(alignment: .leading, spacing: 10) { Text(s.market.rules); Text(s.market.secondaryRules); Text("Closes \(s.market.closeTime.formatted())") }.font(.footnote).foregroundStyle(.secondary).padding(.top, 10)
            }
            Link("Kalshi fee schedule", destination: URL(string: "https://kalshi.com/fee-schedule")!).font(.footnote)
        }
    }
    private var journalView: some View {
        List {
            Section("Local paper account") {
                valueRow("Open maximum loss", money(monitor.journal.openRisk))
                valueRow("Realized hypothetical P/L", money(monitor.journal.realizedProfit))
                valueRow("Available paper risk", money(monitor.journal.availableRisk))
                Text("$25 ceiling includes fees and realized losses. Wins do not increase the ceiling. No real positions are tracked.").font(.caption).foregroundStyle(.secondary)
            }
            Section("Calibration, not validation") {
                valueRow("Unique resolved paired windows", "\(monitor.journal.calibration.count)")
                valueRow("Proxy Brier score", score(monitor.journal.calibration.brier))
                valueRow("Market midpoint Brier score", score(monitor.journal.calibration.marketBrier))
                Text("Lower is better. User-selected samples are biased and not an out-of-sample test. No proven profitable strategy, even if this score improves.").font(.caption).foregroundStyle(.secondary)
                Button("Check official outcomes") { Task { await monitor.refreshSettlements(force: true) } }
                if let message = monitor.settlementMessage { Text(message).font(.caption) }
            }
            Section("Scenarios") {
                if monitor.journal.entries.isEmpty { ContentUnavailableView("No paper scenarios", systemImage: "book.closed", description: Text("Use the Live tab to record a hypothetical position. Nothing is bought.")) }
                ForEach(monitor.journal.entries.reversed()) { entry in
                    VStack(alignment: .leading, spacing: 5) {
                        Text(entry.ticker).font(.caption.monospaced())
                        Text("\(entry.side.rawValue.uppercased()) · \(entry.cost.contracts) contracts · cost \(money(entry.cost.total))").font(.subheadline.bold())
                        Text(entry.result.map { "Official result: \($0.uppercased()) · P/L \(money(entry.profit))" } ?? "Awaiting official YES/NO settlement").font(.caption).foregroundStyle(.secondary)
                        Text(entry.createdAt.formatted()).font(.caption2).foregroundStyle(.secondary)
                    }.padding(.vertical, 4)
                }
            }
        }
    }
    private var methodView: some View {
        List {
            Section("What this app can do") {
                Text("Read public Kalshi BTC 15-minute markets and depth. Refresh while foregrounded, display official rules, calculate estimated after-fee scenarios, and compare local paper forecasts with official outcomes.")
                Text("It cannot place trades, access your account, guarantee profit, or continuously monitor while iOS suspends it.")
            }
            Section("Independent baseline") {
                Text("Uses 61 completed consecutive Coinbase BTC-USD one-minute candles. Volatility is the root mean square of 60 log returns. A zero-log-drift normal endpoint model compares the latest complete close with the official target over remaining time. Kalshi prices are never model inputs.")
                Text("Actual settlement uses a CF Benchmarks BRTI 60-second average. Coinbase is a different source, and an endpoint model does not model that average. No trained model, confidence interval, or independent out-of-sample net-of-cost validation is bundled.")
                Text("The proxy is suppressed for missing/stale/gapped evidence, invalid targets/rules, zero volatility, closed windows, and the final 60 seconds. No favorable-edge alert is enabled.")
            }
            Section("Fees & hypothetical risk") {
                Text("Decimal arithmetic: fee = multiplier × 0.07 × quantity × price × (1 − price). Fee plus position cost rounded up to $0.0001, per the July 7, 2026 schedule. Only a current quadratic series fee is supported. Rule changes or actual fills may differ.")
                Text("A $25 local paper budget is not money available in Kalshi, not a recommendation to stake $25, and not an account-wide loss limit. Default is one contract. Forecasts are hypothetical, uncalibrated research.")
            }
            Section("Sources & privacy") {
                Link("Kalshi public API documentation", destination: URL(string: "https://docs.kalshi.com/api-reference/market/get-market")!)
                Link("Official fee schedule", destination: URL(string: "https://kalshi.com/docs/kalshi-fee-schedule.pdf")!)
                Link("Coinbase candle documentation", destination: URL(string: "https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles")!)
                Text("No analytics, credentials, or account data. Public GET requests go to Kalshi and Coinbase. Paper entries stay in this app’s local storage; deleting the app deletes them.").font(.footnote)
            }
        }
    }
    private func panel<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 12, content: content).frame(maxWidth: .infinity, alignment: .leading).padding(18).background(Color(red: 0.075, green: 0.10, blue: 0.14), in: RoundedRectangle(cornerRadius: 20)).overlay(RoundedRectangle(cornerRadius: 20).stroke(.white.opacity(0.06)))
    }
    private func valueRow(_ title: String, _ value: String) -> some View {
        HStack(alignment: .firstTextBaseline) { Text(title).foregroundStyle(.secondary); Spacer(); Text(value).monospacedDigit().multilineTextAlignment(.trailing) }.font(.subheadline)
    }
    private func money(_ value: Decimal?) -> String {
        guard let value else { return "Unavailable" }
        let formatter = NumberFormatter(); formatter.numberStyle = .currency; formatter.currencyCode = "USD"; formatter.minimumFractionDigits = 2; formatter.maximumFractionDigits = abs(NSDecimalNumber(decimal: value).doubleValue) < 1 ? 4 : 2
        return formatter.string(from: NSDecimalNumber(decimal: value)) ?? "Unavailable"
    }
    private func number(_ value: Decimal?) -> String { value.map { NSDecimalNumber(decimal: $0).stringValue } ?? "Unavailable" }
    private func percent(_ p: Double) -> String { String(format: "%.1f%%", p * 100) }
    private func score(_ value: Double?) -> String { value.map { String(format: "%.4f", $0) } ?? "No resolved pairs" }
}
