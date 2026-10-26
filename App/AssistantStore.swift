import Foundation
import SwiftUI
import SwiftLlama

struct ChatLine: Identifiable, Codable {
    var id: UUID = UUID()
    var role: String
    var text: String
}

@MainActor final class AssistantStore: ObservableObject {
    @Published var messages: [ChatLine] = [] { didSet { persist() } }
    @Published var modelName = UserDefaults.standard.string(forKey: "modelName") ?? ""
    @Published var busy = false
    @Published var status = "Offline"
    private var engine: LlamaService?
    private var task: Task<Void, Never>?
    private var generation = UUID()
    private var docs: URL { FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0] }
    private var history: URL { docs.appendingPathComponent("history.json") }
    private var modelFolder: URL {
        let folder = docs.appendingPathComponent("Models", isDirectory: true)
        try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        return folder
    }
    init() {
        if let data = try? Data(contentsOf: history), let lines = try? JSONDecoder().decode([ChatLine].self, from: data) { messages = lines }
    }
    private func persist() {
        if let data = try? JSONEncoder().encode(messages) { try? data.write(to: history, options: .atomic) }
    }
    func importModel(_ url: URL) throws {
        guard url.pathExtension.lowercased() == "gguf" else {
            throw NSError(domain: "OmniForge", code: 1, userInfo: [NSLocalizedDescriptionKey: "Select a GGUF model"])
        }
        let access = url.startAccessingSecurityScopedResource()
        defer { if access { url.stopAccessingSecurityScopedResource() } }
        let dest = modelFolder.appendingPathComponent(url.lastPathComponent)
        if dest.standardizedFileURL != url.standardizedFileURL {
            let temp = modelFolder.appendingPathComponent(UUID().uuidString + ".gguf")
            defer { try? FileManager.default.removeItem(at: temp) }
            try FileManager.default.copyItem(at: url, to: temp)
            let size = (try FileManager.default.attributesOfItem(atPath: temp.path)[.size] as? NSNumber)?.intValue ?? 0
            guard size > 1_000_000 else { throw NSError(domain: "OmniForge", code: 2, userInfo: [NSLocalizedDescriptionKey: "File too small to be a model"]) }
            if FileManager.default.fileExists(atPath: dest.path) { try FileManager.default.removeItem(at: dest) }
            try FileManager.default.moveItem(at: temp, to: dest)
        }
        modelName = dest.lastPathComponent
        UserDefaults.standard.set(modelName, forKey: "modelName")
        engine = nil
        status = "Model ready"
    }
    func send(_ text: String) {
        let prompt = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !busy && !prompt.isEmpty else { return }
        generation = UUID()
        let token = generation
        messages.append(ChatLine(role: "user", text: prompt))
        let index = messages.count
        messages.append(ChatLine(role: "assistant", text: ""))
        busy = true
        status = "Generating locally"
        task = Task {
            do {
                let path = modelFolder.appendingPathComponent(modelName)
                guard FileManager.default.fileExists(atPath: path.path) else {
                    throw NSError(domain: "OmniForge", code: 3, userInfo: [NSLocalizedDescriptionKey: "Import a GGUF model first"])
                }
                if engine == nil {
                    engine = LlamaService(modelUrl: path, config: .init(batchSize: 256, maxTokenCount: 2048, useGPU: true))
                }
                let history = messages.dropLast().suffix(12)
                var chat = [LlamaChatMessage(role: .system, content: "You are OmniForge, an offline development assistant. Never invent successful tool actions or access to the internet.")]
                for entry in history {
                    chat.append(LlamaChatMessage(role: entry.role == "user" ? .user : .assistant, content: entry.text))
                }
                guard let engine else { return }
                let stream = try await engine.streamCompletion(of: chat, samplingConfig: .init(temperature: 0.65, seed: 42))
                for try await chunk in stream {
                    if Task.isCancelled || generation != token { break }
                    if messages.indices.contains(index) { messages[index].text += chunk }
                }
                if generation == token { status = "Ready" }
            } catch {
                if generation == token && messages.indices.contains(index) {
                    messages[index].text = "Error: \(error.localizedDescription)"
                    status = "Inference error"
                }
            }
            if generation == token { busy = false; task = nil }
        }
    }
    func stop() { generation = UUID(); task?.cancel(); task = nil; busy = false; status = "Stopped" }
    func clear() { stop(); messages.removeAll() }
}
