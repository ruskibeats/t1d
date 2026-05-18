import Foundation
import SwiftUI
import HealthKit

@MainActor
final class HealthDashboardViewModel: ObservableObject {

    // MARK: - Published State

    @Published var summary = DashboardSummary()
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var showError = false

    // MARK: - Services

    private let healthKit = HealthKitManager.shared

    // MARK: - Load All Data

    func loadDashboard() async {
        isLoading = true
        errorMessage = nil

        do {
            // Today's activity
            async let steps = healthKit.fetchTodayStepCount()
            async let calories = healthKit.fetchTodayActiveEnergy()
            async let distance = healthKit.fetchTodayDistance()
            async let exercise = healthKit.fetchTodayExerciseMinutes()

            // Sleep
            async let sleep = healthKit.fetchLastNightSleepDuration()

            // Heart rate
            async let heartRates = healthKit.fetchRecentHeartRates(limit: 1)
            async let hrStats = healthKit.fetchTodayHeartRateStats()

            // Glucose
            async let glucose = healthKit.fetchRecentBloodGlucose(limit: 1)
            async let glucoseStats = healthKit.fetchTodayBloodGlucoseStats()

            // Body
            async let bodyMass = healthKit.fetchLatestBodyMass()
            async let bmi = healthKit.fetchLatestBMI()
            async let bodyFat = healthKit.fetchLatestBodyFat()

            // Vitals
            async let spo2 = healthKit.fetchLatestOxygenSaturation()
            async let respRate = healthKit.fetchLatestRespiratoryRate()
            async let bp = healthKit.fetchRecentBloodPressure(limit: 1)

            // Workouts
            async let workouts = healthKit.fetchRecentWorkouts(limit: 5)

            // Characteristics
            let characteristics = healthKit.fetchUserCharacteristics()

            // Await all
            summary.todaySteps = try await steps
            summary.todayActiveCalories = try await calories
            summary.todayDistanceMeters = try await distance
            summary.todayExerciseMinutes = try await exercise
            summary.lastNightSleepSeconds = try await sleep
            summary.latestHeartRate = try await heartRates.first
            summary.heartRateStats = try await hrStats
            summary.latestGlucose = try await glucose.first
            summary.glucoseStats = try await glucoseStats
            summary.latestBodyMass = try await bodyMass
            summary.latestBMI = try await bmi
            summary.latestBodyFat = try await bodyFat
            summary.latestSpO2 = try await spo2
            summary.latestRespRate = try await respRate
            summary.latestBloodPressure = try await bp.first
            summary.recentWorkouts = try await workouts
            summary.userCharacteristics = characteristics

        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }

        isLoading = false
    }

    // MARK: - Refresh Individual Sections

    func refreshSteps() async {
        do {
            summary.todaySteps = try await healthKit.fetchTodayStepCount()
        } catch {
            handleError(error)
        }
    }

    func refreshHeartRate() async {
        do {
            let rates = try await healthKit.fetchRecentHeartRates(limit: 1)
            summary.latestHeartRate = rates.first
            summary.heartRateStats = try await healthKit.fetchTodayHeartRateStats()
        } catch {
            handleError(error)
        }
    }

    func refreshGlucose() async {
        do {
            let readings = try await healthKit.fetchRecentBloodGlucose(limit: 1)
            summary.latestGlucose = readings.first
            summary.glucoseStats = try await healthKit.fetchTodayBloodGlucoseStats()
        } catch {
            handleError(error)
        }
    }

    func refreshSleep() async {
        do {
            summary.lastNightSleepSeconds = try await healthKit.fetchLastNightSleepDuration()
        } catch {
            handleError(error)
        }
    }

    func refreshWorkouts() async {
        do {
            summary.recentWorkouts = try await healthKit.fetchRecentWorkouts(limit: 5)
        } catch {
            handleError(error)
        }
    }

    // MARK: - Manual Entry

    func saveGlucose(value: Double, date: Date) async {
        do {
            try await healthKit.saveBloodGlucose(value: value, date: date)
            await refreshGlucose()
        } catch {
            handleError(error)
        }
    }

    func saveBodyMass(value: Double, date: Date) async {
        do {
            try await healthKit.saveBodyMass(value: value, date: date)
            summary.latestBodyMass = try await healthKit.fetchLatestBodyMass()
        } catch {
            handleError(error)
        }
    }

    // MARK: - Error Handling

    private func handleError(_ error: Error) {
        errorMessage = error.localizedDescription
        showError = true
    }
}
