import SwiftUI
import Charts

struct ActivityDetailView: View {
    @ObservedObject var viewModel: HealthDashboardViewModel
    @StateObject private var chartVM = ChartViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(spacing: 16) {
                    // Steps section
                    ActivityStepsCard(steps: viewModel.summary.todaySteps)

                    // Calories section
                    ActivityCaloriesCard(
                        active: viewModel.summary.todayActiveCalories,
                        basal: 0 // Could fetch basal if needed
                    )

                    // Distance & Exercise
                    ActivityDistanceCard(
                        distance: viewModel.summary.todayDistanceMeters,
                        exerciseMinutes: viewModel.summary.todayExerciseMinutes
                    )

                    // Weekly chart
                    if !chartVM.dailySteps.isEmpty {
                        ActivityWeeklyChartCard(dailySteps: chartVM.dailySteps)
                    }

                    // Workouts
                    if !viewModel.summary.recentWorkouts.isEmpty {
                        ActivityWorkoutsCard(workouts: viewModel.summary.recentWorkouts)
                    }
                }
                .padding()
            }
            .navigationTitle("Activity")
            .task {
                await chartVM.loadSteps(days: 30)
            }
            .refreshable {
                await chartVM.loadSteps(days: 30)
                await viewModel.loadDashboard()
            }
        }
    }
}

// MARK: - Steps Card

struct ActivityStepsCard: View {
    let steps: Double
    private let goal: Double = 10000

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Label("Steps", systemImage: "figure.walk")
                    .font(.headline)
                Spacer()
                Text("\(Int(steps))")
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundStyle(.green)
            }

            // Progress bar
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 6)
                        .fill(.quaternary)
                        .frame(height: 12)
                    RoundedRectangle(cornerRadius: 6)
                        .fill(.green.gradient)
                        .frame(width: geo.size.width * min(steps / goal, 1.0), height: 12)
                }
            }
            .frame(height: 12)

            HStack {
                Text("\(Int((steps / goal) * 100))% of \(Int(goal)) goal")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                if steps >= goal {
                    Text("🥳 Goal reached!")
                        .font(.caption)
                        .foregroundStyle(.green)
                } else {
                    Text("\(Int(goal - steps)) to go")
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

// MARK: - Calories Card

struct ActivityCaloriesCard: View {
    let active: Double
    let basal: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Label("Energy Burned", systemImage: "flame.fill")
                .font(.headline)

            HStack(spacing: 24) {
                VStack(alignment: .leading) {
                    Text("\(Int(active))")
                        .font(.system(size: 36, weight: .bold, design: .rounded))
                        .foregroundStyle(.red)
                    Text("Active Cal")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                VStack(alignment: .leading) {
                    Text("\(Int(active + basal))")
                        .font(.system(size: 36, weight: .bold, design: .rounded))
                        .foregroundStyle(.orange)
                    Text("Total Cal")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            // Calorie ring
            ZStack {
                Circle()
                    .stroke(.quaternary, lineWidth: 10)
                Circle()
                    .trim(from: 0, to: min(active / 500, 1.0))
                    .stroke(.red.gradient, style: StrokeStyle(lineWidth: 10, lineCap: .round))
                    .rotationEffect(.degrees(-90))

                VStack {
                    Text("\(Int(active))")
                        .font(.title2)
                        .fontWeight(.bold)
                    Text("kcal")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(width: 100, height: 100)
            .frame(maxWidth: .infinity)
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Distance Card

struct.ActivityDistanceCard: View {
    let distance: Double
    let exerciseMinutes: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Label("Distance & Exercise", systemImage: "map.fill")
                .font(.headline)

            HStack(spacing: 24) {
                VStack(alignment: .leading) {
                    Text(String(format: "%.2f", distance / 1000))
                        .font(.title)
                        .fontWeight(.bold)
                    Text("km today")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Divider().frame(height: 40)

                VStack(alignment: .leading) {
                    Text("\(Int(exerciseMinutes))")
                        .font(.title)
                        .fontWeight(.bold)
                    Text("min exercised")
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

// MARK: - Weekly Chart

struct ActivityWeeklyChartCard: View {
    let dailySteps: [DailySteps]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Daily Steps (30 days)")
                .font(.headline)

            Chart(dailySteps) { day in
                BarMark(
                    x: .value("Date", day.date, unit: .day),
                    y: .value("Steps", day.steps)
                )
                .foregroundStyle(day.steps >= 10000 ? .green : .blue)
                .cornerRadius(4)
            }
            .frame(height: 180)
            .chartXAxis {
                AxisMarks(values: .stride(by: .day, count: 7)) { _ in
                    AxisGridLine()
                    AxisValueLabel(format: .dateTime.weekday(.abbreviated))
                }
            }
            .chartYAxis {
                AxisMarks(position: .leading) { value in
                    AxisGridLine()
                    AxisValueLabel {
                        if let steps = value.as(Double.self) {
                            Text("\(Int(steps / 1000))k")
                                .font(.caption2)
                        }
                    }
                }
            }
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Workouts Card

struct ActivityWorkoutsCard: View {
    let workouts: [WorkoutSummary]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Workouts")
                .font(.headline)

            ForEach(workouts) { workout in
                HStack {
                    Image(systemName: "figure.mixed.cardio")
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
                        if workout.distance > 0 {
                            Text(String(format: "%.2f km", workout.distance / 1000))
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                if workout.id != workouts.last?.id {
                    Divider()
                }
            }
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}
