import SwiftUI
import UniformTypeIdentifiers
import CryptoKit

struct MainView: View {
    @EnvironmentObject var store: AssistantStore
    @State private var input = ""
    @State private var modelPicker = false
    @State private var filePicker = false
    @State private var tool = "Read text"
    @State private var result = ""
    @State private var errorText = ""
    @State private var showError = false
    private let tools = ["Read text", "SHA-256", "File header", "JSON format", "Build errors", "Plist inspect"]
    var body: some View {
        TabView {
            NavigationStack {
                VStack {
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 12) {
                            ForEach(store.messages) { message in
                                HStack {
                                    if message.role == "user" { Spacer(minLength: 40) }
                                    Text(message.text.isEmpty ? "Thinking…" : message.text)
                                        .textSelection(.enabled).padding(12)
                                        .background(.secondary.opacity(0.15), in: RoundedRectangle(cornerRadius: 12))
                                    if message.role != "user" { Spacer(minLength: 40) }
                                }
                            }
                        }.padding()
                    }
                    HStack {
                        TextField("Ask OmniForge", text: $input, axis: .vertical).lineLimit(1...5)
                        if store.busy { Button("Stop") { store.stop() } }
                        else { Button("Send") { let value = input; input = ""; store.send(value) }.disabled(input.isEmpty) }
                    }.padding()
                    Text(store.status).font(.caption).foregroundStyle(.secondary)
                }.navigationTitle("OmniForge")
                .toolbar { Button("Clear") { store.clear() } }
            }.tabItem { Label("Chat", systemImage: "bubble.left") }
            NavigationStack {
                List {
                    Picker("Local tool", selection: $tool) {
                        ForEach(tools, id: \.self) { Text($0) }
                    }
                    Button("Select file") { filePicker = true }
                    Text(result).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                    ShareLink(item: result) { Text("Export tool result") }
                }.navigationTitle("Offline tools")
            }.tabItem { Label("Tools", systemImage: "wrench") }
            NavigationStack {
                List {
                    Text(store.modelName.isEmpty ? "No model selected" : store.modelName)
                    Button("Import GGUF model") { modelPicker = true }
                    Text("Inference runs locally. A compatible quantized model is required.")
                }.navigationTitle("Models")
            }.tabItem { Label("Models", systemImage: "cpu") }
        }
        .fileImporter(isPresented: $modelPicker, allowedContentTypes: [UTType(filenameExtension: "gguf") ?? .data]) { r in
            do { try store.importModel(r.get()) } catch { alert(error) }
        }
        .fileImporter(isPresented: $filePicker, allowedContentTypes: [.item]) { r in
            do { try execute(r.get()) } catch { alert(error) }
        }
        .alert("OmniForge error", isPresented: $showError) { Button("OK", role: .cancel) {} } message: { Text(errorText) }
    }
    func alert(_ error: Error) { errorText = error.localizedDescription; showError = true }
    func execute(_ url: URL) throws {
        let access = url.startAccessingSecurityScopedResource()
        defer { if access { url.stopAccessingSecurityScopedResource() } }
        let data = try Data(contentsOf: url, options: .mappedIfSafe)
        switch tool {
        case "SHA-256":
            result = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        case "File header":
            result = data.prefix(256).map { String(format: "%02x", $0) }.joined(separator: " ")
        case "JSON format":
            let object = try JSONSerialization.jsonObject(with: data, options: [.fragmentsAllowed])
            let pretty = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys, .fragmentsAllowed])
            result = String(decoding: pretty, as: UTF8.self)
        case "Plist inspect":
            let plist = try PropertyListSerialization.propertyList(from: data, format: nil)
            result = String(describing: plist)
        case "Build errors":
            result = String(decoding: data, as: UTF8.self).split(separator: "\n").filter {
                $0.localizedCaseInsensitiveContains("error:") || $0.localizedCaseInsensitiveContains("failed")
            }.prefix(100).joined(separator: "\n")
        default:
            result = String(decoding: data.prefix(250_000), as: UTF8.self)
        }
    }
}
