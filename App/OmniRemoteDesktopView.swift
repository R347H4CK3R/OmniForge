import SwiftUI
import WebKit

/// A secure remote desktop viewer for an explicitly configured noVNC endpoint.
/// The Windows VNC server and WebSocket bridge must be installed separately.
/// noVNC supplies touch, pointer and keyboard handling in the web client.
struct OmniRemoteDesktopView: View {
    @AppStorage("remoteDesktopURL") private var address = ""
    @State private var activeURL: URL?
    @State private var error = ""
    var body: some View {
        NavigationStack {
            VStack(spacing: 12) {
                TextField("https://your-private-host/vnc.html", text: $address)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityIdentifier("remoteDesktopAddress")
                HStack {
                    Button("Connect") {
                        guard let url = URL(string: address),
                              url.scheme == "https", url.host != nil,
                              url.user == nil, url.password == nil else {
                            error = "A private HTTPS noVNC URL is required."
                            return
                        }
                        error = ""
                        activeURL = url
                    }
                    .buttonStyle(.borderedProminent)
                    Button("Disconnect", role: .destructive) { activeURL = nil }
                        .disabled(activeURL == nil)
                }
                if !error.isEmpty { Text(error).foregroundStyle(.red).font(.caption) }
                if let url = activeURL {
                    OmniRemoteWebView(url: url)
                        .accessibilityIdentifier("remoteDesktopViewer")
                } else {
                    ContentUnavailableView("Desktop disconnected", systemImage: "desktopcomputer",
                      description: Text("Configure an authenticated noVNC web client behind private HTTPS. Use Disconnect to end viewing."))
                }
            }
            .padding()
            .navigationTitle("Windows Desktop")
            .onDisappear { activeURL = nil }
        }
    }
}

private struct OmniRemoteWebView: UIViewRepresentable {
    let url: URL
    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        configuration.allowsInlineMediaPlayback = true
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.allowsBackForwardNavigationGestures = false
        view.scrollView.isScrollEnabled = false
        view.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData))
        return view
    }
    func updateUIView(_ view: WKWebView, context: Context) {
        if view.url != url { view.load(URLRequest(url: url)) }
    }
    static func dismantleUIView(_ view: WKWebView, coordinator: ()) {
        view.stopLoading()
        view.loadHTMLString("", baseURL: nil)
    }
}
