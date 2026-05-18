import SwiftUI

@main
struct HealthCompanionApp: App {
    @StateObject private var healthKit = HealthKitManager.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(healthKit)
                .onAppear {
                    healthKit.checkAuthorizationStatus()
                }
        }
    }
}
