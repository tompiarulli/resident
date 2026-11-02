import Foundation
import HealthKit
import Observation

/// Reads new HealthKit samples with anchored queries and pushes them to the Resident server.
///
/// Each type keeps its own query anchor, so every sync only sends samples added since the last
/// successful upload. Background delivery wakes the app when the Watch writes new data.
@MainActor
@Observable
final class HealthSync {
    struct TrackedType {
        let identifier: HKQuantityTypeIdentifier
        let unit: HKUnit
        /// Unit label the server's metric catalog expects.
        let unitLabel: String
    }

    static let tracked: [TrackedType] = [
        .init(identifier: .heartRate, unit: .count().unitDivided(by: .minute()), unitLabel: "count/min"),
        .init(identifier: .restingHeartRate, unit: .count().unitDivided(by: .minute()), unitLabel: "count/min"),
        .init(identifier: .heartRateVariabilitySDNN, unit: .secondUnit(with: .milli), unitLabel: "ms"),
        .init(identifier: .respiratoryRate, unit: .count().unitDivided(by: .minute()), unitLabel: "count/min"),
        .init(identifier: .oxygenSaturation, unit: .percent(), unitLabel: "%"),
        .init(identifier: .vo2Max, unit: HKUnit(from: "ml/kg*min"), unitLabel: "mL/kg/min"),
        .init(identifier: .stepCount, unit: .count(), unitLabel: "count"),
        .init(identifier: .activeEnergyBurned, unit: .kilocalorie(), unitLabel: "kcal"),
        .init(identifier: .bodyMass, unit: .gramUnit(with: .kilo), unitLabel: "kg"),
        .init(identifier: .bodyFatPercentage, unit: .percent(), unitLabel: "%"),
    ]

    private static let batchSize = 2000

    private let store = HKHealthStore()
    private(set) var status = "Not synced yet"
    private(set) var isSyncing = false

    func requestAuthorization() async {
        guard HKHealthStore.isHealthDataAvailable() else {
            status = "Health data isn't available on this device"
            return
        }
        let types = Set(Self.tracked.map { HKQuantityType($0.identifier) })
        do {
            try await store.requestAuthorization(toShare: [], read: types)
            status = "Health access requested"
        } catch {
            status = "Authorization failed: \(error.localizedDescription)"
        }
    }

    func startBackgroundDelivery() {
        for tracked in Self.tracked {
            let type = HKQuantityType(tracked.identifier)
            store.enableBackgroundDelivery(for: type, frequency: .hourly) { _, _ in }
            let query = HKObserverQuery(sampleType: type, predicate: nil) { [weak self] _, done, _ in
                Task { @MainActor in await self?.syncAll() }
                done()
            }
            store.execute(query)
        }
    }

    func syncAll() async {
        guard !isSyncing else { return }
        guard let client = SyncClient.fromSettings() else {
            status = "Set a server URL and device token first"
            return
        }
        isSyncing = true
        defer { isSyncing = false }

        var sent = 0
        do {
            for tracked in Self.tracked {
                sent += try await sync(tracked, with: client)
            }
            status = "Synced \(sent) new samples at \(Date.now.formatted(date: .omitted, time: .shortened))"
        } catch {
            status = "Sync failed after \(sent) samples: \(error.localizedDescription)"
        }
    }

    /// Uploads samples for one type in batches, saving the anchor after each successful batch.
    private func sync(_ tracked: TrackedType, with client: SyncClient) async throws -> Int {
        let type = HKQuantityType(tracked.identifier)
        var total = 0
        while true {
            let descriptor = HKAnchoredObjectQueryDescriptor(
                predicates: [.quantitySample(type: type)],
                anchor: AnchorStore.load(for: tracked.identifier),
                limit: Self.batchSize
            )
            let result = try await descriptor.result(for: store)
            let samples = result.addedSamples.map { sample in
                SyncClient.Sample(
                    uuid: sample.uuid.uuidString,
                    type: tracked.identifier.rawValue,
                    value: sample.quantity.doubleValue(for: tracked.unit),
                    unit: tracked.unitLabel,
                    start: sample.startDate,
                    end: sample.endDate,
                    sourceName: sample.sourceRevision.source.name
                )
            }
            if !samples.isEmpty {
                try await client.upload(samples)
            }
            AnchorStore.save(result.newAnchor, for: tracked.identifier)
            total += samples.count
            if samples.count < Self.batchSize { return total }
        }
    }
}

/// Persists HealthKit query anchors between launches.
enum AnchorStore {
    private static func key(_ id: HKQuantityTypeIdentifier) -> String { "anchor.\(id.rawValue)" }

    static func load(for id: HKQuantityTypeIdentifier) -> HKQueryAnchor? {
        guard let data = UserDefaults.standard.data(forKey: key(id)) else { return nil }
        return try? NSKeyedUnarchiver.unarchivedObject(ofClass: HKQueryAnchor.self, from: data)
    }

    static func save(_ anchor: HKQueryAnchor, for id: HKQuantityTypeIdentifier) {
        let data = try? NSKeyedArchiver.archivedData(withRootObject: anchor, requiringSecureCoding: true)
        UserDefaults.standard.set(data, forKey: key(id))
    }
}
