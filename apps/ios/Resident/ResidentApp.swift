import SwiftUI

@main
struct ResidentApp: App {
    @State private var sync = HealthSync()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(sync)
                .task { sync.startBackgroundDelivery() }
        }
    }
}
