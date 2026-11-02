import SwiftUI

struct ContentView: View {
    @Environment(HealthSync.self) private var sync
    @AppStorage("serverURL") private var serverURL = "http://localhost:8000"
    @State private var token = Keychain.deviceToken ?? ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Server URL", text: $serverURL)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("Device token", text: $token)
                        .onSubmit { Keychain.deviceToken = token }
                } header: {
                    Text("Server")
                } footer: {
                    Text("Your data only goes to this server.")
                }

                Section("Apple Health") {
                    Button("Allow access to Health data") {
                        Task { await sync.requestAuthorization() }
                    }
                    Button(sync.isSyncing ? "Syncing…" : "Sync now") {
                        Keychain.deviceToken = token
                        Task { await sync.syncAll() }
                    }
                    .disabled(sync.isSyncing || token.isEmpty)
                }

                Section("Status") {
                    Text(sync.status).foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Resident")
        }
    }
}

#Preview {
    ContentView().environment(HealthSync())
}
