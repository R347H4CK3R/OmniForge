import SwiftUI
import UniformTypeIdentifiers
import CryptoKit

private struct ChatAttachment: Identifiable {
    let id = UUID()
    let name: String
    let contents: String
}

struct MainView: View {
    @EnvironmentObject var store: AssistantStore
    @State private var input = ""
    @FocusState private var inputFocused: Bool
    @State private var attachmentPicker = false
    @State private var ipaReportMode = "Metadata"
    @State private var repackIPA: URL?
    @State private var repackResourcePicker = false
    @State private var repackPath = ""
    @State private var showRepackPath = false
    @State private var attachments: [ChatAttachment] = []
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
                    }.scrollDismissesKeyboard(.interactively)
                    if !attachments.isEmpty {
                        ScrollView(.horizontal) {
                            HStack {
                                ForEach(attachments) { attachment in
                                    HStack {
                                        Text(attachment.name).lineLimit(1)
                                        Button { attachments.removeAll { $0.id == attachment.id } } label: { Image(systemName: "xmark.circle.fill") }
                                    }
                                    .font(.caption).padding(7)
                                    .background(.secondary.opacity(0.14), in: Capsule())
                                }
                            }.padding(.horizontal)
                        }
                    }
                    HStack {
                        Menu {
                            Button("Attach file", systemImage: "doc") { ipaReportMode = "Metadata"; attachmentPicker = true }
                            Menu("Inspect IPA") {
                                Button("Metadata") { ipaReportMode = "Metadata"; attachmentPicker = true }
                                Button("File inventory") { ipaReportMode = "Inventory"; attachmentPicker = true }
                                Button("Mach-O report") { ipaReportMode = "MachO"; attachmentPicker = true }
                                Button("Signing structure") { ipaReportMode = "Signing"; attachmentPicker = true }
                                Button("Export supported resources") { ipaReportMode = "Export"; attachmentPicker = true }
                                Button("Create reconstruction report") { ipaReportMode = "Reconstruct"; attachmentPicker = true }
                                Button("Replace resource in IPA") { ipaReportMode = "Repack"; attachmentPicker = true }
                            }
                            Button("Dismiss keyboard", systemImage: "keyboard.chevron.compact.down") { inputFocused = false }
                        } label: { Image(systemName: "plus.circle.fill").font(.title2) }
                        TextField("Ask OmniForge", text: $input, axis: .vertical).lineLimit(1...5)
                            .focused($inputFocused)
                            .submitLabel(.send)
                        if store.busy { Button("Stop") { store.stop() } }
                        else { Button("Send") { sendMessage() }.disabled(input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && attachments.isEmpty) }
                        Button { inputFocused = false } label: { Image(systemName: "keyboard.chevron.compact.down") }
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
        .fileImporter(isPresented: $attachmentPicker, allowedContentTypes: [.item], allowsMultipleSelection: true) { r in
            do {
                for url in try r.get() {
                    let scoped = url.startAccessingSecurityScopedResource()
                    defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                    if url.pathExtension.lowercased() == "ipa" {
                        let report: String
                        switch ipaReportMode {
                        case "Inventory": report = try IPAWorkbench.inventory(url)
                        case "MachO": report = try IPAWorkbench.executableReport(url)
                        case "Signing": report = try IPAWorkbench.signingReport(url)
                        case "Repack":
                            repackIPA = url
                            repackPath = ""
                            showRepackPath = true
                            report = "Choose the exact resource path in the IPA and replacement file."
                        case "Reconstruct":
                            let output = try IPAReconstruction.generateReport(url)
                            report = "Created reconstruction inventory: Files → On My iPhone → OmniForge → Reconstructions → \(output.lastPathComponent). This does not recover original source."
                        case "Export":
                            let root = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                            let output = root.appendingPathComponent("IPAExports", isDirectory: true).appendingPathComponent(UUID().uuidString, isDirectory: true)
                            let count = try IPAWorkbench.exportResources(url, destination: output)
                            report = "Exported \(count) supported files to Files → On My iPhone → OmniForge → IPAExports → \(output.lastPathComponent). Original IPA unchanged."

                        default: report = try IPAInspector.inspect(url)
                        }
                        attachments.append(ChatAttachment(name: url.lastPathComponent, contents: report))
                        continue
                    }
                    let values = try url.resourceValues(forKeys: [.fileSizeKey])
                    guard (values.fileSize ?? 0) <= 1_000_000 else {
                        throw NSError(domain: "OmniForge", code: 4, userInfo: [NSLocalizedDescriptionKey: "Chat attachments must be 1 MB or smaller; use Tools for larger files."])
                    }
                    let data = try Data(contentsOf: url)
                    guard let text = String(data: data, encoding: .utf8) else {
                        throw NSError(domain: "OmniForge", code: 5, userInfo: [NSLocalizedDescriptionKey: "Chat attachments support UTF-8 text and IPA packages. Other binary formats are not yet supported."])
                    }
                    attachments.append(ChatAttachment(name: url.lastPathComponent, contents: String(text.prefix(100_000))))
                }
            } catch { alert(error) }
        }
        .alert("IPA resource path", isPresented: $showRepackPath) {
            TextField("Payload/App.app/settings.json", text: $repackPath)
            Button("Choose replacement") { repackResourcePicker = true }
            Button("Cancel", role: .cancel) { repackIPA = nil }
        } message: {
            Text("Only supported non-executable resource types. The output is a separate unsigned IPA.")
        }
        .fileImporter(isPresented: $repackResourcePicker, allowedContentTypes: [.item]) { r in
            do {
                guard let ipa = repackIPA else { return }
                let replacement = try r.get()
                let accessIPA = ipa.startAccessingSecurityScopedResource()
                let accessReplacement = replacement.startAccessingSecurityScopedResource()
                defer {
                    if accessIPA { ipa.stopAccessingSecurityScopedResource() }
                    if accessReplacement { replacement.stopAccessingSecurityScopedResource() }
                    repackIPA = nil
                }
                let output = try IPARepacker.replaceResource(ipa: ipa, archivePath: repackPath, replacement: replacement)
                attachments.append(ChatAttachment(name: output.lastPathComponent,
                    contents: "Unsigned repackaged IPA saved to Files → On My iPhone → OmniForge → Repacked → \(output.lastPathComponent). The modified app must be signed before installation."))
            } catch { alert(error) }
        }
        .fileImporter(isPresented: $modelPicker, allowedContentTypes: [UTType(filenameExtension: "gguf") ?? .data]) { r in
            do { try store.importModel(r.get()) } catch { alert(error) }
        }
        .fileImporter(isPresented: $filePicker, allowedContentTypes: [.item]) { r in
            do { try execute(r.get()) } catch { alert(error) }
        }
        .alert("OmniForge error", isPresented: $showError) { Button("OK", role: .cancel) {} } message: { Text(errorText) }
    }
    func sendMessage() {
        let joined = ([input] + attachments.map { "Attached file: \($0.name)\n\($0.contents)" }).joined(separator: "\n\n")
        input = ""
        attachments.removeAll()
        inputFocused = false
        store.send(joined)
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
