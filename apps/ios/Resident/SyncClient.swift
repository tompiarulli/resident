import Foundation

/// Minimal client for the server's HealthKit ingest endpoint.
struct SyncClient: Sendable {
    struct Sample: Encodable, Sendable {
        let uuid: String
        let type: String
        let value: Double
        let unit: String
        let start: Date
        let end: Date
        let sourceName: String
    }

    enum SyncError: LocalizedError {
        case server(status: Int)

        var errorDescription: String? {
            switch self {
            case .server(let status): "Server responded with HTTP \(status)"
            }
        }
    }

    let baseURL: URL
    let token: String

    static func fromSettings() -> SyncClient? {
        guard
            let raw = UserDefaults.standard.string(forKey: "serverURL"),
            let url = URL(string: raw),
            let token = Keychain.deviceToken, !token.isEmpty
        else { return nil }
        return SyncClient(baseURL: url, token: token)
    }

    func upload(_ samples: [Sample]) async throws {
        var request = URLRequest(url: baseURL.appending(path: "api/ingest/healthkit"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(["samples": samples])

        let (_, response) = try await URLSession.shared.data(for: request)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(status) else { throw SyncError.server(status: status) }
    }
}
