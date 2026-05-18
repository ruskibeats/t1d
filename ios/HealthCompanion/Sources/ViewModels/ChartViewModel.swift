import Foundation
import SwiftUI

@MainActor
final class ChartViewModel: ObservableObject {

    @Published var dailySteps: [DailySteps] = []
    @Published var weeklySteps: [DailySteps] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var showError = false

    private let healthKit = HealthKitManager.shared

    func loadSteps(days: Int = 30) async {
        isLoading = true
        do {
            if days <= 7 {
                weeklySteps = try await healthKit.fetchDailySteps(forLast: min(days, 7))
            } else {
                dailySteps = try await healthKit.fetchDailySteps(forLast: days)
            }
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        isLoading = false
    }
}
