import SwiftUI
import WebKit

/// A secure remote desktop viewer for an explicitly configured noVNC endpoint.
/// The Windows VNC server and WebSocket bridge must be installed separately.
/// noVNC supplies touch, pointer and keyboard handling in the web client.
struct OmniRemoteDesktopView: View {
    @AppStorage("remoteDesktopURL") private var address = ""
    @AppStorage("remoteTerminalURL") private var terminalAddress = "https://gaminglaptop-1.tail54e01b.ts.net/terminal/"
    @State private var mode = 0
    @State private var activeURL: URL?
    @State private var error = ""
    @State private var zoom: CGFloat = 1.0
    @State private var panMode = false
    @State private var reconnectID = UUID()
    @State private var webStatus = ""
    @State private var terminalExpanded = false
    var body: some View {
        NavigationStack {
            VStack(spacing: 12) {
                Picker("Remote mode", selection: $mode) {
                    Text("Desktop").tag(0)
                    Text("Terminal").tag(1)
                }
                .pickerStyle(.segmented)
                .onChange(of: mode) { _ in activeURL = nil; error = "" }
                if mode == 1 && !terminalExpanded {
                    VStack(alignment: .leading, spacing: 6) {
                        Label("Connect a Windows terminal", systemImage: "terminal").font(.headline)
                        Text("Your private Windows terminal is configured. Connect Tailscale on your iPhone, tap Connect, then sign in using the dedicated terminal password stored on your laptop.")
                        Text("This is separate from the /installer service. Terminal commands execute as your Windows user; use only with trusted access.")
                    }
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                if !terminalExpanded {
                TextField(mode == 0 ? "https://your-private-host/vnc.html" : "https://your-private-host/terminal/", text: mode == 0 ? $address : $terminalAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityIdentifier("remoteDesktopAddress")
                HStack {
                    Button("Connect") {
                        let target = mode == 0 ? address : terminalAddress
                        guard let url = URL(string: target),
                              url.scheme == "https", url.host != nil,
                              url.user == nil, url.password == nil else {
                            error = "Enter your private HTTPS " + (mode == 0 ? "noVNC desktop" : "authenticated web terminal") + " URL."
                            return
                        }
                        error = ""
                        webStatus = "Opening remote page…"
                        reconnectID = UUID()
                        activeURL = url
                    }
                    .buttonStyle(.borderedProminent)
                    Button("Disconnect", role: .destructive) { activeURL = nil }
                        .disabled(activeURL == nil)
                }
                }
                if activeURL != nil && mode == 1 {
                    HStack {
                        Button(terminalExpanded ? "Show controls" : "Expand terminal") { terminalExpanded.toggle() }
                        Spacer()
                        Text("Swipe down at top of terminal to disconnect").font(.caption2).foregroundStyle(.secondary)
                    }.font(.caption)
                }
                if activeURL != nil && mode == 0 {
                    HStack(spacing: 12) {
                        Button { zoom = max(1.0, zoom - 0.25) } label: {
                            Image(systemName: "minus.magnifyingglass")
                        }.disabled(zoom <= 1.0)
                        Button {
                            zoom = 1.0
                            panMode = false
                        } label: { Text("\(Int(zoom * 100))%") }
                        .accessibilityLabel("Reset zoom")
                        Button { zoom = min(3.0, zoom + 0.25) } label: {
                            Image(systemName: "plus.magnifyingglass")
                        }.disabled(zoom >= 3.0)
                        Toggle("Pan", isOn: $panMode)
                            .labelsHidden()
                            .accessibilityLabel("Pan desktop")
                    }
                    .buttonStyle(.bordered)
                }
                if !error.isEmpty { Text(error).foregroundStyle(.red).font(.caption) }
                if !terminalExpanded && !webStatus.isEmpty { Text(webStatus).font(.caption).foregroundStyle(.secondary).textSelection(.enabled) }
                if let url = activeURL {
                    OmniRemoteWebView(url: url, zoom: mode == 0 ? zoom : 1.0, panMode: mode == 0 ? panMode : true, terminalMode: mode == 1, status: $webStatus)
                        .id(reconnectID)
                        .accessibilityIdentifier("remoteDesktopViewer")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .overlay(alignment: .top) {
                            if mode == 1 {
                                Color.clear.contentShape(Rectangle()).frame(height: 22)
                                    .gesture(DragGesture(minimumDistance: 35).onEnded { value in
                                        if value.translation.height > 90 && abs(value.translation.height) > abs(value.translation.width) {
                                            activeURL = nil
                                            terminalExpanded = false
                                            webStatus = "Terminal disconnected by swipe."
                                        }
                                    })
                            }
                        }
                } else {
                    ContentUnavailableView(mode == 0 ? "Desktop disconnected" : "Terminal disconnected", systemImage: mode == 0 ? "desktopcomputer" : "terminal",
                      description: Text(mode == 0 ? "Configure an authenticated noVNC web client behind private HTTPS." : "Provide a private HTTPS web terminal such as an authenticated ttyd/Wetty deployment. OmniForge does not install a terminal service or expose a shell automatically."))
                }
            }
            .padding(.horizontal, mode == 1 ? 4 : 16)
            .padding(.vertical, mode == 1 ? 4 : 16)
            .navigationTitle(terminalExpanded ? "Terminal" : "Remote Access")
            .onDisappear { activeURL = nil }
        }
    }
}

private struct OmniRemoteWebView: UIViewRepresentable {
    let url: URL
    let zoom: CGFloat
    let panMode: Bool
    let terminalMode: Bool
    @Binding var status: String
    final class Coordinator: NSObject, WKNavigationDelegate {
        var loadedURL: URL?
        var status: Binding<String>?
        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            status?.wrappedValue = "Page loaded: " + (webView.url?.path ?? "/")
        }
        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            status?.wrappedValue = "Navigation failed: " + error.localizedDescription
        }
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            status?.wrappedValue = "Connection failed: " + error.localizedDescription
        }
    }
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        configuration.allowsInlineMediaPlayback = true
        let view = WKWebView(frame: .zero, configuration: configuration)
        context.coordinator.status = $status
        view.navigationDelegate = context.coordinator
        view.allowsBackForwardNavigationGestures = false
        view.scrollView.isScrollEnabled = !terminalMode && panMode
        view.pageZoom = terminalMode ? 1.0 : zoom
        context.coordinator.loadedURL = url
        view.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData))
        return view
    }
    func updateUIView(_ view: WKWebView, context: Context) {
        // Follow server login redirects without reloading the original URL.
        // Only navigate when the user changes the configured endpoint.
        context.coordinator.status = $status
        if context.coordinator.loadedURL != url {
            context.coordinator.loadedURL = url
            view.load(URLRequest(url: url))
        }
        if !terminalMode && abs(view.pageZoom - zoom) > 0.001 { view.pageZoom = zoom }
        view.scrollView.isScrollEnabled = panMode
    }
    static func dismantleUIView(_ view: WKWebView, coordinator: Coordinator) {
        view.stopLoading()
        view.loadHTMLString("", baseURL: nil)
    }
}
