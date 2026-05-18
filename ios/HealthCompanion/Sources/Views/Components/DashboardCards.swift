import SwiftUI

// MARK: - Glucose Card

struct DashboardGlucoseCard: View {
    let glucose: BloodGlucoseSample
    let stats: GlucoseStats?

    private var rangeColor: Color {
        switch glucose.value {
        case ..<70: return .blue      // Low
        case 70...180: return .green  // In range
        case 181...250: return .orange // High
        default: return .red           // Very high
        }
    }

    private var rangeLabel: String {
        switch glucose.value {
        case ..<70: return "Low"
        case 70...180: return "In Range"
        case 181...250: return "High"
        default: return "Very High"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Blood Glucose", systemImage: "drop.fill")
                    .font(.headline)
                    .foregroundStyle(.primary)
                Spacer()
                Text(rangeLabel)
                    .font(.caption)
                    .fontWeight(.semibold)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(rangeColor.opacity(0.15))
                    .foregroundStyle(rangeColor)
                    .clipShape(Capsule())
            }

            HStack(alignment: .lastTextBaseline, spacing: 4) {
                Text("\(Int(glucose.value))")
                    .font(.system(size: 42, weight: .bold, design: .rounded))
                    .foregroundStyle(rangeColor)
                Text("mg/dL")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if let stats = stats, let avg = stats.average {
                HStack(spacing: 16) {
                    StatPill(label: "Avg", value: "\(Int(avg))", color: .secondary)
                    if let min = stats.minimum {
                        StatPill(label: "Min", value: "\(Int(min))", color: .blue)
                    }
                    if let max = stats.maximum {
                        StatPill(label: "Max", value: "\(Int(max))", color: .orange)
                    }
                }
            }

            Text("Last reading: \(glucose.timestamp, style: .relative) ago")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Activity Card

struct DashboardActivityCard: View {
    let steps: Double
    let calories: Double
    let distance: Double
    let exerciseMinutes: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Today's Activity", systemImage: "figure.run")
                .font(.headline)

            HStack(spacing: 0) {
                ActivityRing(
                    value: min(steps / 10000, 1.0),
                    color: .green,
                    icon: "figure.walk"
                )
                ActivityRing(
                    value: min(calories / 500, 1.0),
                    color: .red,
                    icon: "flame.fill"
                )
                ActivityRing(
                    value: min(exerciseMinutes / 30, 1.0),
                    color: .blue,
                    icon: "stopwatch.fill"
                )
            }
            .frame(height: 80)

            HStack(spacing: 20) {
                VStack(alignment: .leading) {
                    Text("\(Int(steps))")
                        .font(.title3)
                        .fontWeight(.semibold)
                    Text("steps")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                VStack(alignment: .leading) {
                    Text("\(Int(calories))")
                        .font(.title3)
                        .fontWeight(.semibold)
                    Text("cal")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                VStack(alignment: .leading) {
                    Text(String(format: "%.1f km", distance / 1000))
                        .font(.title3)
                        .fontWeight(.semibold)
                    Text("distance")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                VStack(alignment: .leading) {
                    Text("\(Int(exerciseMinutes))")
                        .font(.title3)
                        .fontWeight(.semibold)
                    Text("min active")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Heart Rate Card

struct DashboardHeartRateCard: View {
    let sample: HeartRateSample
    let stats: HeartRateStats?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Heart Rate", systemImage: "heart.fill")
                .font(.headline)

            HStack(alignment: .lastTextBaseline, spacing: 4) {
                Text("\(Int(sample.bpm))")
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundStyle(.red)
                Text("bpm")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if let stats = stats {
                HStack(spacing: 16) {
                    if let avg = stats.average {
                        StatPill(label: "Avg", value: "\(Int(avg))", color: .red)
                    }
                    if let min = stats.minimum {
                        StatPill(label: "Min", value: "\(Int(min))", color: .blue)
                    }
                    if let max = stats.maximum {
                        StatPill(label: "Max", value: "\(Int(max))", color: .orange)
                    }
                }
            }

            Text(sample.timestamp, style: .relative) + Text(" ago")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Sleep Card

struct DashboardSleepCard: View {
    let duration: TimeInterval

    private var formatted: String {
        let hours = Int(duration) / 3600
        let minutes = (Int(duration) % 3600) / 60
        return "\(hours)h \(minutes)m"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Last Night's Sleep", systemImage: "moon.fill")
                .font(.headline)

            HStack(alignment: .lastTextBaseline, spacing: 4) {
                Text(formatted)
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundStyle(.indigo)
            }

            // Sleep quality bar
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(.quaternary)
                        .frame(height: 8)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(.indigo.gradient)
                        .frame(width: geo.size.width * min(duration / 28800, 1.0), height: 8)
                }
            }
            .frame(height: 8)

            Text("Goal: 8h")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Body Card

struct DashboardBodyCard: View {
    let mass: BodyMeasurement?
    let bmi: BodyMeasurement?
    let bodyFat: BodyMeasurement?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Body", systemImage: "figure.stand")
                .font(.headline)

            HStack(spacing: 20) {
                if let mass = mass {
                    VStack(alignment: .leading) {
                        Text(String(format: "%.1f", mass.value))
                            .font(.title2)
                            .fontWeight(.semibold)
                        Text("kg")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                if let bmi = bmi {
                    VStack(alignment: .leading) {
                        Text(String(format: "%.1f", bmi.value))
                            .font(.title2)
                            .fontWeight(.semibold)
                        Text("BMI")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                if let fat = bodyFat {
                    VStack(alignment: .leading) {
                        Text(String(format: "%.1f%%", fat.value))
                            .font(.title2)
                            .fontWeight(.semibold)
                        Text("Body Fat")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Blood Pressure Card

struct DashboardBloodPressureCard: View {
    let sample: BloodPressureSample

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Blood Pressure", systemImage: "waveform.path.ecg.rectangle.fill")
                .font(.headline)

            HStack(alignment: .lastTextBaseline, spacing: 4) {
                Text(sample.displayString)
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundStyle(.purple)
                Text("mmHg")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Text(sample.timestamp, style: .relative) + Text(" ago")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Workouts Card

struct DashboardWorkoutsCard: View {
    let workouts: [WorkoutSummary]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Recent Workouts", systemImage: "dumbbell.fill")
                .font(.headline)

            ForEach(workouts.prefix(3)) { workout in
                HStack {
                    Image(systemName: iconFor(workout.activityType))
                        .foregroundStyle(.blue)
                        .frame(width: 24)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(workout.activityName)
                            .font(.subheadline)
                            .fontWeight(.medium)
                        Text(workout.startDate, style: .date)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    VStack(alignment: .trailing, spacing: 2) {
                        Text(workout.durationFormatted)
                            .font(.subheadline)
                            .fontWeight(.medium)
                        if workout.calories > 0 {
                            Text("\(Int(workout.calories)) cal")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                if workout.id != workouts.prefix(3).last?.id {
                    Divider()
                }
            }
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private func iconFor(_ type: HKWorkoutActivityType) -> String {
        switch type {
        case .running: return "figure.run"
        case .cycling: return "bicycle"
        case .swimming: return "figure.pool.swim"
        case .walking: return "figure.walk"
        case .yoga: return "figure.yoga"
        case .strengthTraining: return "dumbbell.fill"
        case .hiit: return "bolt.fill"
        default: return "figure.mixed.cardio"
        }
    }
}

// MARK: - Supporting Views

struct ActivityRing: View {
    let value: Double
    let color: Color
    let icon: String

    var body: some View {
        VStack(spacing: 4) {
            ZStack {
                Circle()
                    .stroke(color.opacity(0.15), lineWidth: 6)
                Circle()
                    .trim(from: 0, to: value)
                    .stroke(color.gradient, style: StrokeStyle(lineWidth: 6, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                Image(systemName: icon)
                    .font(.caption)
                    .foregroundStyle(color)
            }
            .frame(width: 56, height: 56)

            Text("\(Int(value * 100))%")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

struct StatPill: View {
    let label: String
    let value: String
    let color: Color

    var body: some View {
        HStack(spacing: 4) {
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundStyle(color)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(color.opacity(0.1))
        .clipShape(Capsule())
    }
}
