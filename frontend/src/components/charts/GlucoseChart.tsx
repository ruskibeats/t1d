/** @jsxImportSource @emotion/react */
import { Line } from 'react-chartjs-2'
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js'
import { useMemo } from 'react'
import { GlucoseReading } from '@/types'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

interface GlucoseChartProps {
  readings: GlucoseReading[]
  timeRange: '1d' | '3d' | '7d' | '14d'
}

export function GlucoseChart({ readings, timeRange }: GlucoseChartProps) {
  const ordered = useMemo(() => [...readings].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()), [readings])

  const chartData = useMemo(() => {
    const labels = ordered.map((reading) => {
      const date = new Date(reading.timestamp)
      if (timeRange === '1d') return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
      return date.toLocaleDateString('en-GB', { month: 'short', day: 'numeric', hour: '2-digit' })
    })

    const glucoseValues = ordered.map((reading) => reading.glucose_value)

    const gradient = (context: any) => {
      const chart = context.chart
      const { ctx, chartArea } = chart
      if (!chartArea) return 'oklch(0.56 0.19 255 / 0.12)'

      const fill = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top)
      fill.addColorStop(0, 'oklch(0.56 0.19 255 / 0.02)')
      fill.addColorStop(0.52, 'oklch(0.56 0.19 255 / 0.12)')
      fill.addColorStop(1, 'oklch(0.67 0.14 178 / 0.28)')
      return fill
    }

    return {
      labels,
      datasets: [
        {
          label: 'Glucose',
          data: glucoseValues,
          borderColor: 'oklch(0.56 0.19 255)',
          backgroundColor: gradient,
          borderWidth: 3,
          pointRadius: ordered.length > 60 ? 0 : 3,
          pointBackgroundColor: 'oklch(0.56 0.19 255)',
          pointBorderColor: 'oklch(0.98 0.01 245)',
          pointBorderWidth: 2,
          pointHoverRadius: 6,
          pointHoverBackgroundColor: 'oklch(0.67 0.14 178)',
          pointHoverBorderColor: 'oklch(0.98 0.01 245)',
          pointHoverBorderWidth: 3,
          fill: true,
          tension: 0.38,
        },
        {
          label: 'Upper target',
          data: ordered.map(() => 180),
          borderColor: 'oklch(0.67 0.14 178 / 0.72)',
          borderWidth: 1.6,
          borderDash: [7, 5],
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Lower target',
          data: ordered.map(() => 70),
          borderColor: 'oklch(0.67 0.14 178 / 0.72)',
          borderWidth: 1.6,
          borderDash: [7, 5],
          pointRadius: 0,
          fill: false,
        },
      ],
    }
  }, [ordered, timeRange])

  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'index' as const },
    plugins: {
      legend: {
        display: true,
        align: 'end' as const,
        labels: {
          usePointStyle: true,
          boxWidth: 8,
          boxHeight: 8,
          padding: 18,
          color: 'oklch(0.44 0.035 255)',
          font: { size: 11, weight: 700 as const },
          filter: (item: any) => item.text !== 'Lower target',
        },
      },
      tooltip: {
        backgroundColor: 'oklch(0.22 0.045 255 / 0.96)',
        titleColor: 'oklch(0.96 0.012 245)',
        bodyColor: 'oklch(0.92 0.018 245)',
        borderColor: 'oklch(0.42 0.07 255)',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 14,
        callbacks: {
          label: (context: any) => {
            if (context.dataset.label !== 'Glucose') return `${context.dataset.label}: ${context.parsed.y} mg/dL`
            const value: number = context.parsed.y
            const status = value < 70 ? 'low' : value > 180 ? 'high' : 'in range'
            return `Glucose: ${value} mg/dL, ${status}`
          },
        },
      },
    },
    scales: {
      y: {
        min: 45,
        max: 260,
        border: { display: false },
        title: { display: true, text: 'mg/dL', color: 'oklch(0.48 0.035 255)', font: { size: 11, weight: 800 as const } },
        grid: { color: 'oklch(0.6 0.03 255 / 0.11)' },
        ticks: { color: 'oklch(0.48 0.035 255)', font: { size: 11, weight: 650 as const } },
      },
      x: {
        border: { display: false },
        grid: { display: false },
        ticks: { color: 'oklch(0.48 0.035 255)', font: { size: 10, weight: 650 as const }, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
      },
    },
    animation: { duration: 650, easing: 'easeOutQuart' as const },
  }), [])

  if (ordered.length === 0) {
    return (
      <div className="flex h-80 items-center justify-center rounded-[24px] border border-dashed border-[oklch(0.82_0.03_250)] bg-[oklch(0.97_0.012_245)] text-sm font-semibold text-[oklch(0.48_0.035_255)]">
        Connect a sensor or use demo data to draw the trace.
      </div>
    )
  }

  return (
    <div className="h-80 md:h-96">
      <Line data={chartData} options={options} />
    </div>
  )
}
