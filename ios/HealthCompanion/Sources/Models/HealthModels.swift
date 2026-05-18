import Foundation
import HealthKit

// MARK: - Heart Rate

struct HeartRateSample: Identifiable {
    let id = UUID()
    let bpm: Double
    let timestamp: Date
    let source: String
}

struct HeartRateStats {
    let average: Double?
    let minimum: Double?
    let maximum: Double?
}

// MARK: - Blood Glucose

struct BloodGlucoseSample: Identifiable {
    let id = UUID()
    let value: Double
    let unit: String
    let timestamp: Date
    let source: String
}

struct GlucoseStats {
    let average: Double?
    let minimum: Double?
    let maximum: Double?
}

// MARK: - Steps

struct DailySteps: Identifiable {
    let id = UUID()
    let date: Date
    let steps: Double
}

// MARK: - Sleep

struct SleepSession: Identifiable {
    let id = UUID()
    let samples: [HKCategorySample]

    var startDate: Date { samples.last?.startDate ?? Date() }
    var endDate: Date { samples.first?.endDate ?? Date() }
    var duration: TimeInterval { endDate.timeIntervalSince(startDate) }

    var durationFormatted: String {
        let hours = Int(duration) / 3600
        let minutes = (Int(duration) % 3600) / 60
        return "\(hours)h \(minutes)m"
    }
}

// MARK: - Body Measurements

struct BodyMeasurement: Identifiable {
    let id = UUID()
    let value: Double
    let unit: String
    let timestamp: Date
}

// MARK: - Blood Pressure

struct BloodPressureSample: Identifiable {
    let id = UUID()
    let systolic: Double
    let diastolic: Double
    let timestamp: Date

    var displayString: String {
        "\(Int(systolic))/\(Int(diastolic))"
    }
}

// MARK: - Workouts

struct WorkoutSummary: Identifiable {
    let id = UUID()
    let activityType: HKWorkoutActivityType
    let startDate: Date
    let duration: TimeInterval
    let calories: Double
    let distance: Double

    var activityName: String {
        switch activityType {
        case .running: return "Running"
        case .walking: return "Walking"
        case .cycling: return "Cycling"
        case .swimming: return "Swimming"
        case .yoga: return "Yoga"
        case .strengthTraining: return "Strength Training"
        case .hiit: return "HIIT"
        case .tennis: return "Tennis"
        case .basketball: return "Basketball"
        case .soccer: return "Soccer"
        case .hiking: return "Hiking"
        case .dance: return "Dance"
        case .pilates: return "Pilates"
        case .rowing: return "Rowing"
        case .elliptical: return "Elliptical"
        case .stairClimbing: return "Stairs"
        default: return "Workout"
        }
    }

    var durationFormatted: String {
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        if minutes >= 60 {
            let hours = minutes / 60
            let mins = minutes % 60
            return "\(hours)h \(mins)m"
        }
        return "\(minutes)m \(seconds)s"
    }
}

// MARK: - User Characteristics

struct UserCharacteristics {
    let dateOfBirthComponents: DateComponents?
    let biologicalSex: HKBiologicalSexObject
    let bloodType: HKBloodTypeObject

    var age: Int {
        guard let dob = dateOfBirthComponents?.date else { return 0 }
        return Calendar.current.dateComponents([.year], from: dob, to: Date()).year ?? 0
    }

    var sexString: String {
        switch biologicalSex.biologicalSex {
        case .male: return "Male"
        case .female: return "Female"
        case .other: return "Other"
        default: return "Not Set"
        }
    }

    var bloodTypeString: String {
        switch bloodType.bloodType {
        case .aPositive: return "A+"
        case .aNegative: return "A-"
        case .bPositive: return "B+"
        case .bNegative: return "B-"
        case .abPositive: return "AB+"
        case .abNegative: return "AB-"
        case .oPositive: return "O+"
        case .oNegative: return "O-"
        default: return "Unknown"
        }
    }
}

// MARK: - Dashboard Summary

struct DashboardSummary {
    var todaySteps: Double = 0
    var todayActiveCalories: Double = 0
    var todayDistanceMeters: Double = 0
    var todayExerciseMinutes: Double = 0
    var lastNightSleepSeconds: TimeInterval?
    var latestHeartRate: HeartRateSample?
    var heartRateStats: HeartRateStats?
    var latestGlucose: BloodGlucoseSample?
    var glucoseStats: GlucoseStats?
    var latestBodyMass: BodyMeasurement?
    var latestBMI: BodyMeasurement?
    var latestBodyFat: BodyMeasurement?
    var latestSpO2: Double?
    var latestRespRate: Double?
    var latestBloodPressure: BloodPressureSample?
    var recentWorkouts: [WorkoutSummary] = []
    var userCharacteristics: UserCharacteristics?
}
