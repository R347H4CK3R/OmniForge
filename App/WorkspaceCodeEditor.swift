import SwiftUI
import UniformTypeIdentifiers

/// Edits text-based output and clean-room projects; compiled Mach-O is not editable Swift source.
struct WorkspaceCodeEditor: View {
    @State private var files: [URL] = []
    @State private var selected: URL?
    @State private var contents = ""
    @State private var message = "Select an editable source file"
    @State private var importer = false
    @State private var dirty = false

    private var workspace: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("AgentWorkspace", isDirectory: true)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Button("Refresh files") { refresh() }
                Spacer()
                Button("Import source") { importer = true }
            }
            if files.isEmpty {
                ContentUnavailableView("No editable files", systemImage: "doc.text",
                    description: Text("Import a source file, or copy reconstructed project files into OmniForge/Documents/AgentWorkspace."))
            } else {
                Picker("Source file", selection: $selected) {
                    Text("Select a file").tag(Optional<URL>.none)
                    ForEach(files, id: \.self) { file in
                        Text(file.lastPathComponent).tag(Optional(file))
                    }
                }
                .onChange(of: selected) { _, value in
                    if let value { load(value) }
                }
                TextEditor(text: $contents)
                    .font(.system(.footnote, design: .monospaced))
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                    .onChange(of: contents) { _, _ in dirty = true }
                    .border(.secondary.opacity(0.25))
                HStack {
                    Button("Save edits") { save() }
                        .disabled(selected == nil || !dirty)
                    Spacer()
                    ShareLink(item: contents) { Label("Share text", systemImage: "square.and.arrow.up") }
                }
            }
            Text(message).font(.footnote).foregroundStyle(.secondary)
        }
        .padding()
        .navigationTitle("Code Editor")
        .onAppear(perform: refresh)
        .sheet(isPresented: $importer) {
            OmniDocumentPicker(multiple: false, onPick: { urls in
                importer = false
                guard let file = urls.first else { return }
                do {
                    let allowed = Set(["swift", "c", "h", "m", "mm", "cpp", "hpp", "py", "js", "ts", "json", "md", "txt", "xml", "plist"])
                    guard allowed.contains(file.pathExtension.lowercased()) else {
                        throw NSError(domain: "OmniForge.Editor", code: 1,
                            userInfo: [NSLocalizedDescriptionKey: "Only editable text-based source files are supported"])
                    }
                    let data = try Data(contentsOf: file)
                    guard data.count <= 1_000_000, String(data: data, encoding: .utf8) != nil else {
                        throw NSError(domain: "OmniForge.Editor", code: 2,
                            userInfo: [NSLocalizedDescriptionKey: "File must be UTF-8 text under 1 MB"])
                    }
                    try FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: true)
                    let destination = workspace.appendingPathComponent(UUID().uuidString + "-" + file.lastPathComponent)
                    try data.write(to: destination, options: .atomic)
                    refresh()
                    selected = destination
                    load(destination)
                } catch { message = error.localizedDescription }
            }, onCancel: { importer = false })
        }
    }

    private func refresh() {
        try? FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: true)
        let allowed = Set(["swift", "c", "h", "m", "mm", "cpp", "hpp", "py", "js", "ts", "json", "md", "txt", "xml", "plist"])
        files = (try? FileManager.default.contentsOfDirectory(at: workspace, includingPropertiesForKeys: nil))?
            .filter { allowed.contains($0.pathExtension.lowercased()) }
            .sorted { $0.lastPathComponent < $1.lastPathComponent } ?? []
    }
    private func load(_ file: URL) {
        do {
            let data = try Data(contentsOf: file)
            guard data.count <= 1_000_000, let text = String(data: data, encoding: .utf8) else {
                message = "Source file exceeds 1 MB or is not UTF-8"; return
            }
            contents = text
            dirty = false
            message = "Loaded " + file.lastPathComponent
        } catch { message = error.localizedDescription }
    }
    private func save() {
        guard let selected else { return }
        do {
            guard contents.utf8.count <= 1_000_000 else {
                message = "Cannot save text larger than 1 MB"; return
            }
            try Data(contents.utf8).write(to: selected, options: .atomic)
            dirty = false
            message = "Saved " + selected.lastPathComponent
        } catch { message = error.localizedDescription }
    }
}
