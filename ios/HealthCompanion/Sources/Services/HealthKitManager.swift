import Foundation
import HealthKit

// MARK: - Authorization Status

enum HealthKitAuthorizationState {
    case notDetermined
    case authorized
    case denied
    case unavailable
}

// MARK: - HealthKit Manager

/// Central service for all HealthKit interactions.
/// Handles authorization, availability checks, and all read queries.
@MainActor
final class HealthKitManager: ObservableObject {

    // MARK: - Properties

    static let shared = HealthKitManager()

    let healthStore = HKHealthStore()

    @Published var authorizationState: HealthKitAuthorizationState = .notDetermined
    @Published var isHealthDataAvailable: Bool = false

    // MARK: - Data Types to Read

    private let typesToRead: Set<HKObjectType> = [
        // Vitals
        HKQuantityType(.heartRate),
        HKQuantityType(.restingHeartRate),
        HKQuantityType(.heartRateVariabilitySDNN),
        HKQuantityType(.oxygenSaturation),
        HKQuantityType(.bloodPressureSystolic),
        HKQuantityType(.bloodPressureDiastolic),
        HKQuantityType(.bloodGlucose),
        HKQuantityType(.bodyTemperature),
        HKQuantityType(.respiratoryRate),

        // Activity
        HKQuantityType(.stepCount),
        HKQuantityType(.distanceWalkingRunning),
        HKQuantityType(.activeEnergyBurned),
        HKQuantityType(.basalEnergyBurned),
        HKQuantityType(.appleExerciseTime),
        HKQuantityType(.appleStandTime),
        HKQuantityType(.appleMoveTime),

        // Body
        HKQuantityType(.bodyMass),
        HKQuantityType(.bodyMassIndex),
        HKQuantityType(.height),
        HKQuantityType(.bodyFatPercentage),
        HKQuantityType(.leanBodyMass),
        HKQuantityType(.waistCircumference),

        // Nutrition
        HKQuantityType(.dietaryEnergyConsumed),
        HKQuantityType(.dietaryCarbohydrates),
        HKQuantityType(.dietaryProtein),
        HKQuantityType(.dietaryFatTotal),
        HKQuantityType(.dietaryFiber),
        HKQuantityType(.dietarySugar),
        HKQuantityType(.dietarySodium),
        HKQuantityType(.dietaryWater),

        // Sleep
        HKCategoryType(.sleepAnalysis),

        // Workouts
        HKWorkoutType.workoutType(),

        // Characteristics
        HKCharacteristicType(.dateOfBirth),
        HKCharacteristicType(.biologicalSex),
        HKCharacteristicType(.bloodType),
    ]

    private let typesToWrite: Set<HKSampleType> = [
        HKQuantityType(.bloodGlucose),
        HKQuantityType(.bodyMass),
        HKQuantityType(.dietaryEnergyConsumed),
        HKQuantityType(.dietaryCarbohydrates),
        HKQuantityType(.dietaryProtein),
        HKQuantityType(.dietaryFatTotal),
        HKQuantityType(.dietaryWater),
    ]

    // MARK: - Init

    private init() {
        isHealthDataAvailable = HKHealthStore.isHealthDataAvailable()
        if !isHealthDataAvailable {
            authorizationState = .unavailable
        }
    }

    // MARK: - Authorization

    func requestAuthorization() async {
        guard isHealthDataAvailable else {
            authorizationState = .unavailable
            return
        }

        do {
            try await healthStore.requestAuthorization(
                toShare: typesToWrite,
                read: typesToRead
            )
            authorizationState = .authorized
        } catch {
            authorizationState = .denied
        }
    }

    func checkAuthorizationStatus() {
        guard isHealthDataAvailable else {
            authorizationState = .unavailable
            return
        }

        // Check a representative type to determine if we've been asked
        let status = healthStore.authorizationStatus(for: HKQuantityType(.heartRate))
        switch status {
        case .notDetermined:
            authorizationState = .notDetermined
        case .sharingAuthorized:
            authorizationState = .authorized
        case .sharingDenied:
            authorizationState = .denied
        @unknown default:
            authorizationState = .notDetermined
        }
    }

    // MARK: - Heart Rate

    func fetchRecentHeartRates(limit: Int = 50) async throws -> [HeartRateSample] {
        let heartRateType = HKQuantityType(.heartRate)
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: heartRateType)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: limit
        )

        let results = try await descriptor.result(for: healthStore)
        return results.map { sample in
            let bpm = sample.quantity.doubleValue(
                for: HKUnit.count().unitDivided(by: .minute())
            )
            return HeartRateSample(
                bpm: bpm,
                timestamp: sample.endDate,
                source: sample.sourceRevision.source.name
            )
        }
    }

    func fetchTodayHeartRateStats() async throws -> HeartRateStats {
        let (startOfDay, endOfDay) = todayRange()
        let predicate = HKQuery.predicateForSamples(withStart: startOfDay, end: endOfDay)
        let heartRateType = HKQuantityType(.heartRate)
        let samplePredicate = HKSamplePredicate.quantitySample(type: heartRateType, predicate: predicate)

        let avgQuery = HKStatisticsQueryDescriptor(predicate: samplePredicate, options: .discreteAverage)
        let minQuery = HKStatisticsQueryDescriptor(predicate: samplePredicate, options: .discreteMin)
        let maxQuery = HKStatisticsQueryDescriptor(predicate: samplePredicate, options: .discreteMax)

        async let avgResult = avgQuery.result(for: healthStore)
        async let minResult = minQuery.result(for: healthStore)
        async let maxResult = maxQuery.result(for: healthStore)

        let unit = HKUnit.count().unitDivided(by: .minute())
        let avg = try await avgResult?.averageQuantity()?.doubleValue(for: unit)
        let min = try await minResult?.minimumQuantity()?.doubleValue(for: unit)
        let max = try await maxResult?.maximumQuantity()?.doubleValue(for: unit)

        return HeartRateStats(average: avg, minimum: min, maximum: max)
    }

    // MARK: - Blood Glucose

    func fetchRecentBloodGlucose(limit: Int = 50) async throws -> [BloodGlucoseSample] {
        let glucoseType = HKQuantityType(.bloodGlucose)
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: glucoseType)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: limit
        )

        let results = try await descriptor.result(for: healthStore)
        let unit = HKUnit.gramUnit(with: .milli).unitDivided(by: .literUnit(with: .deci))

        return results.map { sample in
            let value = sample.quantity.doubleValue(for: unit)
            return BloodGlucoseSample(
                value: value,
                unit: "mg/dL",
                timestamp: sample.endDate,
                source: sample.sourceRevision.source.name
            )
        }
    }

    func fetchTodayBloodGlucoseStats() async throws -> GlucoseStats {
        let (startOfDay, endOfDay) = todayRange()
        let predicate = HKQuery.predicateForSamples(withStart: startOfDay, end: endOfDay)
        let glucoseType = HKQuantityType(.bloodGlucose)
        let samplePredicate = HKSamplePredicate.quantitySample(type: glucoseType, predicate: predicate)

        let avgQuery = HKStatisticsQueryDescriptor(predicate: samplePredicate, options: .discreteAverage)
        let minQuery = HKStatisticsQueryDescriptor(predicate: samplePredicate, options: .discreteMin)
        let maxQuery = HKStatisticsQueryDescriptor(predicate: samplePredicate, options: .discreteMax)

        let unit = HKUnit.gramUnit(with: .milli).unitDivided(by: .literUnit(with: .deci))

        async let avgResult = avgQuery.result(for: healthStore)
        async let minResult = minQuery.result(for: healthStore)
        async let maxResult = maxQuery.result(for: healthStore)

        let avg = try await avgResult?.averageQuantity()?.doubleValue(for: unit)
        let min = try await minResult?.minimumQuantity()?.doubleValue(for: unit)
        let max = try await maxResult?.maximumQuantity()?.doubleValue(for: unit)

        return GlucoseStats(average: avg, minimum: min, maximum: max)
    }

    // MARK: - Steps

    func fetchTodayStepCount() async throws -> Double {
        let (startOfDay, endOfDay) = todayRange()
        let predicate = HKQuery.predicateForSamples(withStart: startOfDay, end: endOfDay)
        let stepType = HKQuantityType(.stepCount)
        let samplePredicate = HKSamplePredicate.quantitySample(type: stepType, predicate: predicate)

        let query = HKStatisticsQueryDescriptor(predicate: samplePredicate, options: .cumulativeSum)
        let result = try await query.result(for: healthStore)
        return result?.sumQuantity()?.doubleValue(for: .count()) ?? 0
    }

    func fetchDailySteps(forLast days: Int) async throws -> [DailySteps] {
        let (startDate, endDate, anchorDate) = dayRange(days: days)
        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: endDate)
        let stepType = HKQuantityType(.stepCount)
        let samplePredicate = HKSamplePredicate.quantitySample(type: stepType, predicate: predicate)

        let query = HKStatisticsCollectionQueryDescriptor(
            predicate: samplePredicate,
            options: .cumulativeSum,
            anchorDate: anchorDate,
            intervalComponents: DateComponents(day: 1)
        )

        let collection = try await query.result(for: healthStore)
        var dailySteps: [DailySteps] = []

        collection.enumerateStatistics(from: startDate, to: endDate) { statistics, _ in
            let steps = statistics.sumQuantity()?.doubleValue(for: .count()) ?? 0
            dailySteps.append(DailySteps(date: statistics.startDate, steps: steps))
        }

        return dailySteps
    }

    // MARK: - Active Energy

    func fetchTodayActiveEnergy() async throws -> Double {
        let (startOfDay, endOfDay) = todayRange()
        let predicate = HKQuery.predicateForSamples(withStart: startOfDay, end: endOfDay)
        let energyType = HKQuantityType(.activeEnergyBurned)
        let samplePredicate = HKSamplePredicate.quantitySample(type: energyType, predicate: predicate)

        let query = HKStatisticsQueryDescriptor(predicate: samplePredicate, options: .cumulativeSum)
        let result = try await query.result(for: healthStore)
        return result?.sumQuantity()?.doubleValue(for: .kilocalorie()) ?? 0
    }

    // MARK: - Distance

    func fetchTodayDistance() async throws -> Double {
        let (startOfDay, endOfDay) = todayRange()
        let predicate = HKQuery.predicateForSamples(withStart: startOfDay, end: endOfDay)
        let distanceType = HKQuantityType(.distanceWalkingRunning)
        let samplePredicate = HKSamplePredicate.quantitySample(type: distanceType, predicate: predicate)

        let query = HKStatisticsQueryDescriptor(predicate: samplePredicate, options: .cumulativeSum)
        let result = try await query.result(for: healthStore)
        return result?.sumQuantity()?.doubleValue(for: .meter()) ?? 0
    }

    // MARK: - Exercise Time

    func fetchTodayExerciseMinutes() async throws -> Double {
        let (startOfDay, endOfDay) = todayRange()
        let predicate = HKQuery.predicateForSamples(withStart: startOfDay, end: endOfDay)
        let exerciseType = HKQuantityType(.appleExerciseTime)
        let samplePredicate = HKSamplePredicate.quantitySample(type: exerciseType, predicate: predicate)

        let query = HKStatisticsQueryDescriptor(predicate: samplePredicate, options: .cumulativeSum)
        let result = try await query.result(for: healthStore)
        return result?.sumQuantity()?.doubleValue(for: .minute()) ?? 0
    }

    // MARK: - Sleep

    func fetchRecentSleepSessions(limit: Int = 7) async throws -> [SleepSession] {
        let sleepType = HKCategoryType(.sleepAnalysis)
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.categorySample(type: sleepType)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: limit * 10 // Multiple samples per session
        )

        let results = try await descriptor.result(for: healthStore)

        // Group consecutive sleep samples into sessions
        var sessions: [SleepSession] = []
        var currentSessionSamples: [HKCategorySample] = []

        for sample in results {
            if let last = currentSessionSamples.last {
                // If gap > 2 hours, start new session
                let gap = last.startDate.timeIntervalSince(sample.endDate)
                if gap > 7200 {
                    if !currentSessionSamples.isEmpty {
                        sessions.append(SleepSession(samples: currentSessionSamples))
                        if sessions.count >= limit { break }
                    }
                    currentSessionSamples = [sample]
                } else {
                    currentSessionSamples.append(sample)
                }
            } else {
                currentSessionSamples.append(sample)
            }
        }

        if !currentSessionSamples.isEmpty && sessions.count < limit {
            sessions.append(SleepSession(samples: currentSessionSamples))
        }

        return sessions
    }

    func fetchLastNightSleepDuration() async throws -> TimeInterval? {
        let calendar = Calendar.current
        let now = Date()
        let yesterday = calendar.date(byAdding: .day, value: -1, to: now)!
        let startOfYesterday = calendar.startOfDay(for: yesterday)
        let startOfToday = calendar.startOfDay(for: now)

        let sleepType = HKCategoryType(.sleepAnalysis)
        let predicate = HKQuery.predicateForSamples(withStart: startOfYesterday, end: startOfToday)
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.categorySample(type: sleepType, predicate: predicate)],
            sortDescriptors: [SortDescriptor(\.startDate, order: .forward)],
            limit: 100
        )

        let results = try await descriptor.result(for: healthStore)
        guard !results.isEmpty else { return nil }

        // Calculate total time in bed/asleep
        var totalSleep: TimeInterval = 0
        for sample in results {
            // Only count actual sleep (inBed, asleepCore, asleepDeep, asleepREM)
            let value = sample.value
            if value != HKCategoryValueSleepAnalysis.inBed.rawValue {
                totalSleep += sample.endDate.timeIntervalSince(sample.startDate)
            }
        }

        return totalSleep > 0 ? totalSleep : nil
    }

    // MARK: - Body Measurements

    func fetchLatestBodyMass() async throws -> BodyMeasurement? {
        let massType = HKQuantityType(.bodyMass)
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: massType)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: 1
        )

        guard let sample = try await descriptor.result(for: healthStore).first else { return nil }
        let kg = sample.quantity.doubleValue(for: .gramUnit(with: .kilo))
        return BodyMeasurement(value: kg, unit: "kg", timestamp: sample.endDate)
    }

    func fetchLatestBMI() async throws -> BodyMeasurement? {
        let bmiType = HKQuantityType(.bodyMassIndex)
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: bmiType)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: 1
        )

        guard let sample = try await descriptor.result(for: healthStore).first else { return nil }
        let bmi = sample.quantity.doubleValue(for: .count())
        return BodyMeasurement(value: bmi, unit: "", timestamp: sample.endDate)
    }

    func fetchLatestBodyFat() async throws -> BodyMeasurement? {
        let fatType = HKQuantityType(.bodyFatPercentage)
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: fatType)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: 1
        )

        guard let sample = try await descriptor.result(for: healthStore).first else { return nil }
        let pct = sample.quantity.doubleValue(for: .percent()) * 100
        return BodyMeasurement(value: pct, unit: "%", timestamp: sample.endDate)
    }

    // MARK: - Blood Pressure

    func fetchRecentBloodPressure(limit: Int = 20) async throws -> [BloodPressureSample] {
        let systolicType = HKQuantityType(.bloodPressureSystolic)
        let diastolicType = HKQuantityType(.bloodPressureDiastolic)

        let systolicDescriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: systolicType)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: limit
        )
        let diastolicDescriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: diastolicType)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: limit
        )

        async let systolicResults = systolicDescriptor.result(for: healthStore)
        async let diastolicResults = diastolicDescriptor.result(for: healthStore)

        let systolics = try await systolicResults
        let diastolics = try await diastolicResults

        let mmHg = HKUnit.millimeterOfMercury()

        // Pair by closest timestamp
        var samples: [BloodPressureSample] = []
        for sys in systolics {
            let sysValue = sys.quantity.doubleValue(for: mmHg)
            // Find closest diastolic within 60 seconds
            if let dia = diastolics.first(where: { abs($0.endDate.timeIntervalSince(sys.endDate)) < 60 }) {
                let diaValue = dia.quantity.doubleValue(for: mmHg)
                samples.append(BloodPressureSample(
                    systolic: sysValue,
                    diastolic: diaValue,
                    timestamp: sys.endDate
                ))
            }
        }

        return Array(samples.prefix(limit))
    }

    // MARK: - Oxygen Saturation

    func fetchLatestOxygenSaturation() async throws -> Double? {
        let spo2Type = HKQuantityType(.oxygenSaturation)
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: spo2Type)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: 1
        )

        guard let sample = try await descriptor.result(for: healthStore).first else { return nil }
        return sample.quantity.doubleValue(for: .percent()) * 100
    }

    // MARK: - Respiratory Rate

    func fetchLatestRespiratoryRate() async throws -> Double? {
        let respType = HKQuantityType(.respiratoryRate)
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: respType)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: 1
        )

        guard let sample = try await descriptor.result(for: healthStore).first else { return nil }
        return sample.quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute()))
    }

    // MARK: - Workouts

    func fetchRecentWorkouts(limit: Int = 10) async throws -> [WorkoutSummary] {
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.workout()],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: limit
        )

        let results = try await descriptor.result(for: healthStore)

        return results.map { workout in
            let duration = workout.endDate.timeIntervalSince(workout.startDate)
            let calories = workout.totalEnergyBurned?.doubleValue(for: .kilocalorie()) ?? 0
            let distance = workout.totalDistance?.doubleValue(for: .meter()) ?? 0

            return WorkoutSummary(
                activityType: workout.workoutActivityType,
                startDate: workout.startDate,
                duration: duration,
                calories: calories,
                distance: distance
            )
        }
    }

    // MARK: - User Characteristics

    func fetchUserCharacteristics() -> UserCharacteristics? {
        guard isHealthDataAvailable else { return nil }

        do {
            let dob = try healthStore.dateOfBirthComponents()
            let sex = try healthStore.biologicalSex()
            let bloodType = try healthStore.bloodType()

            return UserCharacteristics(
                dateOfBirthComponents: dob,
                biologicalSex: sex,
                bloodType: bloodType
            )
        } catch {
            return nil
        }
    }

    // MARK: - Save Data

    func saveBloodGlucose(value: Double, date: Date) async throws {
        let glucoseType = HKQuantityType(.bloodGlucose)
        let unit = HKUnit.gramUnit(with: .milli).unitDivided(by: .literUnit(with: .deci))
        let quantity = HKQuantity(unit: unit, doubleValue: value)

        let sample = HKQuantitySample(
            type: glucoseType,
            quantity: quantity,
            start: date,
            end: date
        )

        try await healthStore.save(sample)
    }

    func saveBodyMass(value: Double, date: Date) async throws {
        let massType = HKQuantityType(.bodyMass)
        let quantity = HKQuantity(unit: .gramUnit(with: .kilo), doubleValue: value)

        let sample = HKQuantitySample(
            type: massType,
            quantity: quantity,
            start: date,
            end: date
        )

        try await healthStore.save(sample)
    }

    // MARK: - Helpers

    private func todayRange() -> (start: Date, end: Date) {
        let calendar = Calendar.current
        let startOfDay = calendar.startOfDay(for: Date())
        let endOfDay = calendar.date(byAdding: .day, value: 1, to: startOfDay)!
        return (startOfDay, endOfDay)
    }

    private func dayRange(days: Int) -> (start: Date, end: Date, anchor: Date) {
        let calendar = Calendar.current
        let endOfDay = calendar.startOfDay(
            for: calendar.date(byAdding: .day, value: 1, to: Date())!
        )
        let startOfDay = calendar.date(byAdding: .day, value: -days, to: endOfDay)!
        return (startOfDay, endOfDay, endOfDay)
    }
}
