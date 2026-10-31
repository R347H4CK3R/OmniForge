import SwiftUI
import WebKit

/// A secure remote desktop viewer for an explicitly configured noVNC endpoint.
/// The Windows VNC server and WebSocket bridge must be installed separately.
/// noVNC supplies touch, pointer and keyboard handling in the web client.
struct OmniRemoteDesktopView: View {
    @AppStorage("remoteDesktopURL") private var address = ""
    @AppStorage("remoteTerminalURL") private var terminalAddress = ""
    @State private var mode = 0
    @State private var activeURL: URL?
    @State private var error = ""
    @State private var zoom: CGFloat = 1.0
    @State private var panMode = false
    var body: some View {
        NavigationStack {
            VStack(spacing: 12) {
                Picker("Remote mode", selection: $mode) {
                    Text("Desktop").tag(0)
                    Text("Terminal").tag(1)
                }
                .pickerStyle(.segmented)
                .onChange(of: mode) { _ in activeURL = nil; error = "" }
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
                        activeURL = url
                    }
                    .buttonStyle(.borderedProminent)
                    Button("Disconnect", role: .destructive) { activeURL = nil }
                        .disabled(activeURL == nil)
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
                if let url = activeURL {
                    OmniRemoteWebView(url: url, zoom: mode == 0 ? zoom : 1.0, panMode: mode == 0 ? panMode : true)
                        .accessibilityIdentifier("remoteDesktopViewer")
                } else {
                    ContentUnavailableView(mode == 0 ? "Desktop disconnected" : "Terminal disconnected", systemImage: mode == 0 ? "desktopcomputer" : "terminal",
                      description: Text(mode == 0 ? "Configure an authenticated noVNC web client behind private HTTPS." : "Provide a private HTTPS web terminal such as an authenticated ttyd/Wetty deployment. OmniForge does not install a terminal service or expose a shell automatically."))
                }
            }
            .padding()
            .navigationTitle("Remote Access")
            .onDisappear { activeURL = nil }
        }
    }
}

private struct OmniRemoteWebView: UIViewRepresentable {
    let url: URL
    let zoom: CGFloat
    let panMode: Bool
    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        configuration.allowsInlineMediaPlayback = true
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.allowsBackForwardNavigationGestures = false
        view.scrollView.isScrollEnabled = panMode
        view.pageZoom = zoom
        view.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData))
        return view
    }
    func updateUIView(_ view: WKWebView, context: Context) {
        if view.url != url { view.load(URLRequest(url: url)) }
        if abs(view.pageZoom - zoom) > 0.001 { view.pageZoom = zoom }
        view.scrollView.isScrollEnabled = panMode
    }
    static func dismantleUIView(_ view: WKWebView, coordinator: ()) {
        view.stopLoading()
        view.loadHTMLString("", baseURL: nil)
    }
}
