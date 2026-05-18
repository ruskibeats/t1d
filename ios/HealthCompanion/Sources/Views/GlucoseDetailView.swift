import SwiftUI
import Charts

struct GlucoseDetailView: View {
    @ObservedObject var viewModel: HealthDashboardViewModel
    @State private var glucoseReadings: [BloodGlucoseSample] = []
    @State private var isLoading = false
    @State private var showAddGlucose = false

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(spacing: 16) {
                    // Current reading
                    if let current = viewModel.summary.latestGlucose {
                        GlucoseCurrentCard(glucose: current, stats: viewModel.summary.glucoseStats)
                    }

                    // Chart
                    if !glucoseReadings.isEmpty {
                        GlucoseChartCard(readings: glucoseReadings)
                    }

                    // Recent readings list
                    GlucoseHistoryCard(readings: glucoseReadings)
                }
                .padding()
            }
            .navigationTitle("Glucose")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showAddGlucose = true
                    } label: {
                        Image(systemName: "plus.circle.fill")
                    }
                }
            }
            .sheet(isPresented: $showAddGlucose) {
                AddGlucoseSheet(viewModel: viewModel)
            }
            .task {
                await loadReadings()
            }
            .refreshable {
                await loadReadings()
                await viewModel.refreshGlucose()
            }
        }
    }

    private func loadReadings() async {
        isLoading = true
        do {
            glucoseReadings = try await HealthKitManager.shared.fetchRecentBloodGlucose(limit: 100)
        } catch {
            viewModel.errorMessage = error.localizedDescription
            viewModel.showError = true
        }
        isLoading = false
    }
}

// MARK: - Current Glucose Card

struct GlucoseCurrentCard: View {
    let glucose: BloodGlucoseSample
    let stats: GlucoseStats?

    private var status: (color: Color, label: String) {
        switch glucose.value {
        case ..<70: return (.blue, "Low")
        case 70...180: return (.green, "In Range")
        case 181...250: return (.orange, "High")
        default: return (.red, "Very High")
        }
    }

    var body: some View {
        VStack(spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Current")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    HStack(alignment: .lastTextBaseline, spacing: 4) {
                        Text("\(Int(glucose.value))")
                            .font(.system(size: 56, weight: .bold, design: .rounded))
                            .foregroundStyle(status.color)
                        Text("mg/dL")
                            .font(.title3)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 4) {
                    Text(status.label)
                        .font(.headline)
                        .fontWeight(.bold)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(status.color.opacity(0.15))
                        .foregroundStyle(status.color)
                        .clipShape(Capsule())
                    Text(glucose.timestamp, style: .relative)
                        .font(.caption)
                        .foregroundStyle(.secondary) + Text(" ago")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            // Range indicator bar
            GlucoseRangeBar(value: glucose.value)

            if let stats = stats {
                Divider()
                HStack(spacing: 24) {
                    if let avg = stats.average {
                        VStack {
                            Text("\(Int(avg))")
                                .font(.title3)
                                .fontWeight(.semibold)
                            Text("Average")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    if let min = stats.minimum {
                        VStack {
                            Text("\(Int(min))")
                                .font(.title3)
                                .fontWeight(.semibold)
                                .foregroundStyle(.blue)
                            Text("Lowest")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    if let max = stats.maximum {
                        VStack {
                            Text("\(Int(max))")
                                .font(.title3)
                                .fontWeight(.semibold)
                                .foregroundStyle(.orange)
                            Text("Highest")
                                .font(.caption)
                                .foregroundStyle(.secondary)
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

// MARK: - Glucose Range Bar

struct GlucoseRangeBar: View {
    let value: Double

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                // Background segments
                HStack(spacing: 1) {
                    Rectangle().fill(.blue.opacity(0.3))  // Low
                    Rectangle().fill(.green.opacity(0.3)) // Normal
                    Rectangle().fill(.orange.opacity(0.3)) // High
                    Rectangle().fill(.red.opacity(0.3))   // Very high
                }
                .frame(height: 8)
                .clipShape(Capsule())

                // Indicator
                let position = positionFor(value, width: geo.size.width)
                Circle()
                    .fill(.white)
                    .frame(width: 14, height: 14)
                    .shadow(radius: 2)
                    .overlay {
                        Circle()
                            .stroke(Color.primary, lineWidth: 2)
                    }
                    .position(x: position, y: 4)
            }
        }
        .frame(height: 14)

        HStack {
            Text("<70")
                .font(.caption2)
                .foregroundStyle(.blue)
            Spacer()
            Text("70-180")
                .font(.caption2)
                .foregroundStyle(.green)
            Spacer()
            Text("181-250")
                .font(.caption2)
                .foregroundStyle(.orange)
            Spacer()
            Text(">250")
                .font(.caption2)
                .foregroundStyle(.red)
        }
    }

    private func positionFor(_ value: Double, width: CGFloat) -> CGFloat {
        let clamped = min(max(value, 40), 300)
        let range: Double = 300 - 40
        return CGFloat((clamped - 40) / range) * width
    }
}

// MARK: - Glucose Chart

struct GlucoseChartCard: View {
    let readings: [BloodGlucoseSample]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Recent Readings")
                .font(.headline)

            Chart {
                // Target range
                RectangleMark(
                    xStart: .value("Start", readings.last?.timestamp ?? Date()),
                    xEnd: .value("End", readings.first?.timestamp ?? Date()),
                    yStart: .value("Low", 70),
                    yEnd: .value("High", 180)
                )
                .foregroundStyle(.green.opacity(0.1))

                ForEach(readings.reversed()) { reading in
                    LineMark(
                        x: .value("Time", reading.timestamp),
                        y: .value("Glucose", reading.value)
                    )
                    .foregroundStyle(.red.gradient)
                    .interpolationMethod(.catmullRom)

                    PointMark(
                        x: .value("Time", reading.timestamp),
                        y: .value("Glucose", reading.value)
                    )
                    .foregroundStyle(colorFor(reading.value))
                    .symbolSize(20)
                }
            }
            .frame(height: 200)
            .chartYScale(domain: 40...300)
            .chartYAxis {
                AxisMarks(position: .leading) { value in
                    AxisGridLine()
                    AxisValueLabel {
                        if let intValue = value.as(Double.self) {
                            Text("\(Int(intValue))")
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

    private func colorFor(_ value: Double) -> Color {
        switch value {
        case ..<70: return .blue
        case 70...180: return .green
        case 181...250: return .orange
        default: return .red
        }
    }
}

// MARK: - Glucose History

struct GlucoseHistoryCard: View {
    let readings: [BloodGlucoseSample]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("History")
                .font(.headline)

            ForEach(readings.prefix(20)) { reading in
                HStack {
                    Circle()
                        .fill(colorFor(reading.value))
                        .frame(width: 10, height: 10)

                    Text("\(Int(reading.value)) mg/dL")
                        .font(.subheadline)
                        .fontWeight(.medium)

                    Spacer()

                    Text(reading.timestamp, style: .time)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(reading.timestamp, style: .date)
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
                if reading.id != readings.prefix(20).last?.id {
                    Divider()
                }
            }
        }
        .padding()
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private func colorFor(_ value: Double) -> Color {
        switch value {
        case ..<70: return .blue
        case 70...180: return .green
        case 181...250: return .orange
        default: return .red
        }
    }
}

// MARK: - Add Glucose Sheet

struct AddGlucoseSheet: View {
    @ObservedObject var viewModel: HealthDashboardViewModel
    @Environment(\.dismiss) var dismiss
    @State private var value: String = ""
    @State private var date = Date()

    var body: some View {
        NavigationStack {
            Form {
                Section("Reading") {
                    HStack {
                        Text("Value")
                        Spacer()
                        TextField("mg/dL", text: $value)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                        Text("mg/dL")
                            .foregroundStyle(.secondary)
                    }

                    DatePicker("Date & Time", selection: $date, displayedComponents: [.date, .hourAndMinute])
                }

                Section {
                    Button("Save") {
                        if let val = Double(value) {
                            Task {
                                await viewModel.saveGlucose(value: val, date: date)
                                dismiss()
                            }
                        }
                    }
                    .disabled(value.isEmpty)
                }
            }
            .navigationTitle("Add Glucose")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}
