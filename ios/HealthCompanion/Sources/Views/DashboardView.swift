import SwiftUI

struct DashboardView: View {
    @StateObject private var viewModel = HealthDashboardViewModel()
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardHomeView(viewModel: viewModel)
                .tabItem {
                    Label("Dashboard", systemImage: "heart.text.square.fill")
                }
                .tag(0)

            GlucoseDetailView(viewModel: viewModel)
                .tabItem {
                    Label("Glucose", systemImage: "drop.fill")
                }
                .tag(1)

            ActivityDetailView(viewModel: viewModel)
                .tabItem {
                    Label("Activity", systemImage: "figure.run")
                }
                .tag(2)

            VitalsDetailView(viewModel: viewModel)
                .tabItem {
                    Label("Vitals", systemImage: "waveform.path.ecg")
                }
                .tag(3)

            SettingsView(viewModel: viewModel)
                .tabItem {
                    Label("Settings", systemImage: "gearshape.fill")
                }
                .tag(4)
        }
        .tint(.red)
        .task {
            await viewModel.loadDashboard()
        }
        .refreshable {
            await viewModel.loadDashboard()
        }
        .alert("Error", isPresented: $viewModel.showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(viewModel.errorMessage ?? "An unknown error occurred")
        }
    }
}

// MARK: - Dashboard Home

struct DashboardHomeView: View {
    @ObservedObject var viewModel: HealthDashboardViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(spacing: 16) {
                    // Glucose Card (prominent for T1D)
                    if let glucose = viewModel.summary.latestGlucose {
                        DashboardGlucoseCard(glucose: glucose, stats: viewModel.summary.glucoseStats)
                    }

                    // Activity Ring Summary
                    DashboardActivityCard(
                        steps: viewModel.summary.todaySteps,
                        calories: viewModel.summary.todayActiveCalories,
                        distance: viewModel.summary.todayDistanceMeters,
                        exerciseMinutes: viewModel.summary.todayExerciseMinutes
                    )

                    // Heart Rate
                    if let hr = viewModel.summary.latestHeartRate {
                        DashboardHeartRateCard(sample: hr, stats: viewModel.summary.heartRateStats)
                    }

                    // Sleep
                    if let sleep = viewModel.summary.lastNightSleepSeconds {
                        DashboardSleepCard(duration: sleep)
                    }

                    // Body Metrics
                    DashboardBodyCard(
                        mass: viewModel.summary.latestBodyMass,
                        bmi: viewModel.summary.latestBMI,
                        bodyFat: viewModel.summary.latestBodyFat
                    )

                    // Blood Pressure
                    if let bp = viewModel.summary.latestBloodPressure {
                        DashboardBloodPressureCard(sample: bp)
                    }

                    // Recent Workouts
                    if !viewModel.summary.recentWorkouts.isEmpty {
                        DashboardWorkoutsCard(workouts: viewModel.summary.recentWorkouts)
                    }
                }
                .padding()
            }
            .navigationTitle("Health Companion")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await viewModel.loadDashboard() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
        }
    }
}
