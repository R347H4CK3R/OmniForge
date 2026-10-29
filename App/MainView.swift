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
    @StateObject private var updates = OmniForgeUpdates()
    @StateObject private var ipaUploader = IPAJobUploader()
    @State private var directIPAPicker = false
    @State private var agentSecret = ""
    @State private var searxngURL = UserDefaults.standard.string(forKey: "searxngURL") ?? ""
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
            chatTab
            toolsTab
            rebuildTab
            OmniRemoteDesktopView().tabItem { Label("Desktop", systemImage: "desktopcomputer") }
            modelsTab
            updatesTab
        }
        .sheet(isPresented: $directIPAPicker) {
            OmniDocumentPicker(multiple: false, onPick: { urls in
                directIPAPicker = false
                guard let file = urls.first else { return }
                let destination = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".ipa")
                do {
                    try FileManager.default.copyItem(at: file, to: destination)
                    Task {
                        await ipaUploader.submit(destination)
                        try? FileManager.default.removeItem(at: destination)
                    }
                } catch { ipaUploader.message = error.localizedDescription }
            }, onCancel: { directIPAPicker = false })
        }
        .sheet(isPresented: $attachmentPicker) { OmniDocumentPicker(multiple: true, onPick: { urls in
            attachmentPicker = false
            do {
                for url in urls {
                    let scoped = url.startAccessingSecurityScopedResource()
                    defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                    if url.pathExtension.lowercased() == "ipa" {
                        // Retain an authorized copy for the local agent to inspect in later turns.
                        let folder = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                            .appendingPathComponent("AgentWorkspace", isDirectory: true)
                        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
                        let saved = folder.appendingPathComponent(UUID().uuidString + ".ipa")
                        try FileManager.default.copyItem(at: url, to: saved)
                        let report: String
                        switch ipaReportMode {
                        case "Inventory": report = try IPAWorkbench.inventory(url)
                        case "MachO": report = try IPAWorkbench.executableReport(url)
                        case "ReverseEngineer": report = try IPAReverseEngineer.report(url)
                        case "Signing": report = try IPAWorkbench.signingReport(url)
                        case "Repack":
                            let temporary = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".ipa")
                            try FileManager.default.copyItem(at: url, to: temporary)
                            repackIPA = temporary
                            repackPath = ""
                            showRepackPath = true
                            report = "Choose the exact resource path in the IPA and replacement file."
                        case "AutoRebuild": report = try AutoRebuildAdvisor.report(for: url)
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
        }, onCancel: {}) }
        .alert("IPA resource path", isPresented: $showRepackPath) {
            TextField("Payload/App.app/settings.json", text: $repackPath)
            Button("Choose replacement") { repackResourcePicker = true }
            Button("Cancel", role: .cancel) { if let ipa = repackIPA { try? FileManager.default.removeItem(at: ipa) }; repackIPA = nil }
        } message: {
            Text("Only supported non-executable resource types. The output is a separate unsigned IPA.")
        }
        .sheet(isPresented: $repackResourcePicker) { OmniDocumentPicker(multiple: false, onPick: { urls in
            repackResourcePicker = false
            do {
                guard let ipa = repackIPA else { return }
                guard let replacement = urls.first else { return }
                let accessReplacement = replacement.startAccessingSecurityScopedResource()
                defer {
                    if accessReplacement { replacement.stopAccessingSecurityScopedResource() }
                    try? FileManager.default.removeItem(at: ipa)
                    repackIPA = nil
                }
                let output = try IPARepacker.replaceResource(ipa: ipa, archivePath: repackPath, replacement: replacement)
                attachments.append(ChatAttachment(name: output.lastPathComponent,
                    contents: "Unsigned repackaged IPA saved to Files → On My iPhone → OmniForge → Repacked → \(output.lastPathComponent). The modified app must be signed before installation."))
            } catch { alert(error) }
        }, onCancel: {}) }
        .sheet(isPresented: $modelPicker) { OmniDocumentPicker(multiple: false, onPick: { urls in
            modelPicker = false
            do { try store.importModel(urls.first ?? URL(fileURLWithPath: "/dev/null")) } catch { alert(error) }
        }, onCancel: {}) }
        .sheet(isPresented: $filePicker) { OmniDocumentPicker(multiple: false, onPick: { urls in
            filePicker = false
            do { try execute(urls.first ?? URL(fileURLWithPath: "/dev/null")) } catch { alert(error) }
        }, onCancel: {}) }
        .alert("OmniForge error", isPresented: $showError) { Button("OK", role: .cancel) {} } message: { Text(errorText) }
    }
    private var chatTab: some View {
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
                    }.scrollDismissesKeyboard(.immediately)
                    .simultaneousGesture(TapGesture().onEnded { inputFocused = false })
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
                                Button("Reverse engineer IPA") { ipaReportMode = "ReverseEngineer"; attachmentPicker = true }
                                Button("Signing structure") { ipaReportMode = "Signing"; attachmentPicker = true }
                                Button("Export supported resources") { ipaReportMode = "Export"; attachmentPicker = true }
                                Button("Automatically choose rebuild or patch path") { ipaReportMode = "AutoRebuild"; attachmentPicker = true }
                                Button("Create reconstruction report") { ipaReportMode = "Reconstruct"; attachmentPicker = true }
                                Button("Replace resource in IPA") { ipaReportMode = "Repack"; attachmentPicker = true }
                            }
                            Button("Dismiss keyboard", systemImage: "keyboard.chevron.compact.down") { inputFocused = false }
                        } label: { Image(systemName: "plus.circle.fill").font(.title2) }
                        TextField("Ask OmniForge", text: $input, axis: .vertical).lineLimit(1...5)
                            .focused($inputFocused)
                            .submitLabel(.send)
                            .onSubmit { sendMessage() }
                        if store.busy { Button("Stop") { store.stop() } }
                        else { Button("Send") { sendMessage() }.disabled(input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && attachments.isEmpty) }
                        Button { inputFocused = false } label: { Image(systemName: "keyboard.chevron.compact.down") }
                    }.padding()
                    Text(store.status).font(.caption).foregroundStyle(.secondary)
                }.navigationTitle("OmniForge")
                .toolbar {
                    ToolbarItemGroup(placement: .keyboard) {
                        Spacer()
                        Button("Done") { inputFocused = false }
                    }
                }
                .toolbar { Button("Clear") { store.clear() } }
            }.tabItem { Label("Chat", systemImage: "bubble.left") }
    }

    private var toolsTab: some View {
        NavigationStack {
                List {
                    Picker("Local tool", selection: $tool) {
                        ForEach(tools, id: \.self) { Text($0) }
                    }
                    Button("Show available AI tools") { result = OmniToolCatalog.help }
                    Button("Select file") { filePicker = true }
                    Text(result).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                    ShareLink(item: result) { Text("Export tool result") }
                }.navigationTitle("Offline tools")
            }.tabItem { Label("Tools", systemImage: "wrench") }
    }

    private var rebuildTab: some View {
        NavigationStack {
                List {
                    Section("Editable source workspace") {
                        NavigationLink("Open Code Editor") { WorkspaceCodeEditor() }
                        Text("Edit recovered pseudocode and clean-room SwiftUI projects. This cannot magically recompile a decompiled IPA.")
                            .font(.footnote)
                    }
                    Section("On-device reconstruction") {
                        Button("Select IPA and export reconstruction inventory") {
                            ipaReportMode = "Reconstruct"
                            attachmentPicker = true
                        }
                        Button("Reverse engineer an IPA locally") {
                            ipaReportMode = "ReverseEngineer"
                            attachmentPicker = true
                        }
                        Text("The local report identifies files and metadata. It cannot reconstruct an original application's Swift source or full UI.")
                            .font(.footnote)
                    }
                    Section("Submit IPA directly") {
                        TextField("Private repo: owner/repo", text: $ipaUploader.repo)
                            .textInputAutocapitalization(.never).autocorrectionDisabled()
                        SecureField("Fine-grained GitHub token", text: $ipaUploader.token)
                        Button("Choose IPA and start analysis") { directIPAPicker = true }
                            .disabled(ipaUploader.working)
                        Text(ipaUploader.message).font(.footnote)
                        Text("Use a private repository with OmniForge's IPA Workbench workflow installed. Uploads contain the selected IPA and require your explicit authorization. Never use a public repository for proprietary apps.")
                            .font(.footnote)
                    }
                    Section("GitHub reconstruction tools") {
                        Link("Generate editable SwiftUI project", destination: URL(string: "https://github.com/R347H4CK3R/OmniForge/actions/workflows/ipa-workbench.yml")!)
                        Link("Run Ghidra pseudocode analysis", destination: URL(string: "https://github.com/R347H4CK3R/OmniForge/actions/workflows/ghidra-analysis.yml")!)
                        Link("View workflow results", destination: URL(string: "https://github.com/R347H4CK3R/OmniForge/actions")!)
                        Text("Upload an authorized IPA as a GitHub Release asset, then run the matching workflow with the release tag and filename. The macOS workbench generates an editable clean-room project; Ghidra produces pseudocode reports. Importing the result directly into this app is not yet supported.")
                            .font(.footnote)
                    }
                }
                .navigationTitle("Reconstruction")
            }.tabItem { Label("Rebuild", systemImage: "hammer") }
    }

    private var modelsTab: some View {
        NavigationStack {
                List {
                    Section("On-device autonomous agent") {
                        Toggle("Use local agent in Chat", isOn: $store.localAgentEnabled)
                        Toggle("Permit edits in AgentWorkspace", isOn: $store.agentCanEdit)
                            .disabled(!store.localAgentEnabled)
                        Text("The agent can inspect files, create or edit text files inside OmniForge/Documents/AgentWorkspace, validate JSON, analyze accessible IPAs and retrieve HTTPS pages. There is no fixed execution-step limit. You can stop it; repeated identical actions are halted to prevent loops. It cannot run arbitrary shell commands or Xcode on iOS.")
                            .font(.footnote)
                    }
                    Section("Free internet search") {
                        TextField("SearXNG HTTPS URL", text: $searxngURL)
                            .textInputAutocapitalization(.never).autocorrectionDisabled()
                            .keyboardType(.URL)
                        Button("Save search endpoint") {
                            UserDefaults.standard.set(searxngURL.trimmingCharacters(in: .whitespacesAndNewlines), forKey: "searxngURL")
                        }
                        Text("Use /search followed by a query. SearXNG must support JSON output.")
                            .font(.footnote)
                    }
                    Section("AI engine") {
                        Toggle("Use my own online server", isOn: $store.onlineEnabled)
                        if store.onlineEnabled {
                            TextField("HTTPS endpoint", text: $store.onlineEndpoint)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .keyboardType(.URL)
                            SecureField("Private agent access key", text: $agentSecret)
                                .textContentType(.password)
                            Button("Save private agent key") {
                                OnlineModelClient.saveKey(agentSecret)
                                agentSecret = ""
                            }
                            TextField("Model ID (example qwen3:8b)", text: $store.onlineModel)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                            Text("Use https://YOUR-TAILSCALE-DEVICE/v1/chat/completions. Your laptop runs Ollama; no paid AI API is required. When offline mode is selected, your imported GGUF runs on this iPhone.")
                                .font(.footnote)
                        }
                    }
                    Text(store.modelName.isEmpty ? "No model selected" : store.modelName)
                    Button("Import GGUF from Files") { modelPicker = true }
                    Button("Scan local model files") { store.scanModels() }
                    if !store.localModels.isEmpty {
                        Section("Available local GGUF models") {
                            ForEach(store.localModels, id: \.path) { url in
                                Button {
                                    store.selectModel(url)
                                } label: {
                                    HStack {
                                        Image(systemName: store.modelName == url.lastPathComponent ? "checkmark.circle.fill" : "circle")
                                        Text(url.lastPathComponent).lineLimit(2)
                                    }
                                }
                            }
                        }
                    }
                    Section("LiveContainer fallback") {
                        Text("If the Files picker cannot select a GGUF, use LiveContainer's app data/file manager to place the .gguf file in OmniForge/Documents/Models or OmniForge/Documents. Return here and tap Scan local model files, then select it.")
                            .font(.footnote)
                    }
                    Text("Inference runs locally. A compatible quantized model is required.")
                }.navigationTitle("Models")
            }.tabItem { Label("Models", systemImage: "cpu") }
    }

    private var updatesTab: some View {
        NavigationStack {
                List {
                    LabeledContent("Installed build", value: "#\(updates.installedBuild)")
                    Text(updates.status).font(.subheadline)
                    Button("Check for update") { Task { await updates.check() } }
                        .disabled(updates.checking)
                    if updates.updateAvailable, let url = updates.buildURL {
                        Link("Get latest unsigned IPA on GitHub", destination: url)
                    }
                    Text("Updates require internet. GitHub builds produce unsigned IPAs; signing and installation must be completed with your existing sideloading method. OmniForge cannot silently replace itself.")
                        .font(.footnote).foregroundStyle(.secondary)
                }.navigationTitle("Updates")
                    .task { await updates.check() }
            }.tabItem { Label("Updates", systemImage: "arrow.down.circle") }
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
