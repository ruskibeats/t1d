import SwiftUI

struct ContentView: View {
    @EnvironmentObject var healthKit: HealthKitManager

    var body: some View {
        Group {
            switch healthKit.authorizationState {
            case .notDetermined:
                AuthorizationRequestView()
            case .authorized:
                DashboardView()
            case .denied:
                AuthorizationDeniedView()
            case .unavailable:
                HealthKitUnavailableView()
            }
        }
    }
}

// MARK: - Authorization Request

struct AuthorizationRequestView: View {
    @EnvironmentObject var healthKit: HealthKitManager

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "heart.text.square.fill")
                .font(.system(size: 80))
                .foregroundStyle(.red.gradient)

            Text("Health Companion")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("Connect to Apple Health to view your glucose, heart rate, activity, sleep, and more — all in one place.")
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Spacer()

            Button {
                Task {
                    await healthKit.requestAuthorization()
                }
            } label: {
                Label("Connect to Health", systemImage: "heart.fill")
                    .font(.headline)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(.red.gradient)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
            }
            .padding(.horizontal, 32)
            .padding(.bottom, 48)
        }
    }
}

// MARK: - Authorization Denied

struct AuthorizationDeniedView: View {
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "lock.shield.fill")
                .font(.system(size: 60))
                .foregroundStyle(.orange)

            Text("Health Access Denied")
                .font(.title2)
                .fontWeight(.semibold)

            Text("Please enable Health access in Settings → Privacy & Security → Health → Health Companion.")
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Button("Open Settings") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
            .buttonStyle(.borderedProminent)
        }
    }
}

// MARK: - HealthKit Unavailable

struct HealthKitUnavailableView: View {
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 60))
                .foregroundStyle(.yellow)

            Text("HealthKit Unavailable")
                .font(.title2)
                .fontWeight(.semibold)

            Text("HealthKit is not available on this device. An iPhone is required.")
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
        }
    }
}
