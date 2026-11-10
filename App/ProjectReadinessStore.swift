import Foundation
import Combine

private final class ReadinessRedirectGuard: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

@MainActor
final class ProjectReadinessStore: ObservableObject {
    @Published private(set) var report: ProjectReadiness.Report?
    @Published private(set) var message = "Refresh to inspect your host workspace. No builds, updates or installations are started."
    @Published private(set) var loading = false
    private var task: Task<Void, Never>?
    private var session: URLSession?
    private var generation = UUID()

    func cancel() {
        generation = UUID()
        task?.cancel(); task = nil
        session?.invalidateAndCancel(); session = nil
        loading = false; report = nil
        message = "Refresh to read a current host snapshot."
    }
    func refresh(endpoint: String) {
        guard !loading else { return }
        report = nil
        let url: URL
        do { url = try ProjectReadiness.endpoint(endpoint) }
        catch { message = error.localizedDescription; return }
        guard let key = OnlineModelClient.readKey(), !key.isEmpty,
              !key.contains(where: { $0.isWhitespace }) else {
            message = "Save your private AI API token in Settings first."; return
        }
        let requestID = UUID(); generation = requestID
        loading = true; message = "Reading host readiness…"
        task = Task {
            let configuration = URLSessionConfiguration.ephemeral
            configuration.urlCache = nil
            configuration.httpCookieStorage = nil
            configuration.urlCredentialStorage = nil
            configuration.timeoutIntervalForRequest = 10
            configuration.timeoutIntervalForResource = 20
            let session = URLSession(configuration: configuration, delegate: ReadinessRedirectGuard(), delegateQueue: nil)
            self.session = session
            defer {
                session.invalidateAndCancel()
                if generation == requestID { loading = false; self.session = nil; task = nil }
            }
            do {
                var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 10)
                request.setValue("Bearer " + key, forHTTPHeaderField: "Authorization")
                request.setValue("application/json", forHTTPHeaderField: "Accept")
                request.setValue("no-store", forHTTPHeaderField: "Cache-Control")
                let (bytes, response) = try await session.bytes(for: request)
                guard let http = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
                switch http.statusCode {
                case 200: break
                case 401, 403: throw ProjectReadiness.Failure.message("Authorization rejected. Check your saved AI API token in Settings.")
                case 404: throw ProjectReadiness.Failure.message("This host does not support project readiness yet. Update the host service separately.")
                case 300...399: throw ProjectReadiness.Failure.message("Host redirected the request. No credentials were forwarded. Check the saved endpoint.")
                default: throw ProjectReadiness.Failure.message("Host readiness unavailable (HTTP \(http.statusCode)).")
                }
                var data = Data()
                for try await byte in bytes {
                    try Task.checkCancellation()
                    guard data.count < 524288 else { throw ProjectReadiness.Failure.message("Readiness report exceeds the size limit.") }
                    data.append(byte)
                }
                let parsed = try ProjectReadiness.decode(data)
                try Task.checkCancellation()
                guard generation == requestID else { return }
                report = parsed; message = "Read-only snapshot · \(parsed.generated_at)"
            } catch {
                guard generation == requestID, !Task.isCancelled else { return }
                message = (error as? ProjectReadiness.Failure)?.localizedDescription
                    ?? "Could not read a valid readiness report. Check the host connection and try again."
            }
        }
    }
}
