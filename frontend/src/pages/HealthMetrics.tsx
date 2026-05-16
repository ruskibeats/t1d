/** @jsxImportSource @emotion/react */
import { useState, useEffect } from 'react'
import { Activity, Moon, TrendingUp, Clock3 } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { StatCard } from '@/components/ui/StatCard'
import { useHealthMetrics } from '@/hooks/useHealthMetrics'
import { cn } from '@/lib/utils'

const ranges = [
  { label: '1D', value: '1d' },
  { label: '3D', value: '3d' },
  { label: '7D', value: '7d' },
  { label: '14D', value: '14d' },
] as const

export function HealthMetricsPage() {
  const [timeRange, setTimeRange] = useState<'1d' | '3d' | '7d' | '14d'>('3d')
  const { metrics, fetchMetrics } = useHealthMetrics()

  useEffect(() => { fetchMetrics(timeRange) }, [timeRange])

  const glucoseData = metrics.filter(m => m.metric_type === 'blood_glucose')
  const exerciseData = metrics.filter(m => m.metric_type === 'exercise_minutes')
  const sleepData = metrics.filter(m => m.metric_type === 'sleep_hours')
  const foodData = metrics.filter(m => m.metric_type === 'calories')
  const avgGlucose = glucoseData.length ? (glucoseData.reduce((s, m) => s + m.value, 0) / glucoseData.length).toFixed(0) : '--'
  const totalExercise = exerciseData.reduce((s, m) => s + m.value, 0).toFixed(0)
  const totalSleep = sleepData.reduce((s, m) => s + m.value / 60, 0).toFixed(1)
  const totalCalories = foodData.reduce((s, m) => s + m.value, 0).toFixed(0)

  return (
    <div className="page-shell space-y-7">
      <div className="flex items-center justify-between">
        <div>
          <div className="kicker"><span className="kicker-dot" /> Unified view</div>
          <h2 className="mt-2 text-2xl font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">Health metrics</h2>
        </div>
        <div className="flex rounded-2xl border border-[oklch(0.86_0.02_250)] bg-[oklch(0.98_0.01_245/0.72)] p-1">
          {ranges.map(r => (
            <button key={r.value} onClick={() => setTimeRange(r.value)}
              className={cn('rounded-xl px-4 py-2 text-sm font-black transition', timeRange === r.value ? 'bg-[oklch(0.23_0.045_255)] text-white shadow-lg' : 'text-[oklch(0.45_0.035_255)] hover:bg-[oklch(0.93_0.018_245)]')}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard title="Avg Glucose" value={avgGlucose as string} subtitle="mg/dL" icon={Activity} variant={typeof avgGlucose === 'string' && parseFloat(avgGlucose) > 180 ? 'warning' : 'success'} />
        <StatCard title="Exercise" value={totalExercise as string} subtitle="minutes" icon={TrendingUp} variant="success" />
        <StatCard title="Sleep" value={totalSleep as string} subtitle="hours" icon={Moon} variant="default" />
        <StatCard title="Calories" value={totalCalories as string} subtitle="kcal" icon={Clock3} variant="default" />
      </div>

      <Card className="p-5">
        <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">Combined metrics</h3>
        <div className="space-y-4">
          {glucoseData.length > 0 && (
            <div>
              <p className="text-sm font-bold text-[oklch(0.48_0.035_255)]">Glucose</p>
              <div className="mt-1 h-20 rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
                <div className="flex h-full items-end gap-[2px]">
                  {glucoseData.slice(-48).map((m, i) => (
                    <div key={i} className="flex-1 rounded-t-sm"
                      style={{ height: `${Math.min((m.value / 250) * 100, 100)}%`, backgroundColor: m.value > 180 ? 'oklch(0.75 0.15 72)' : m.value < 70 ? 'oklch(0.72 0.18 27)' : 'oklch(0.72 0.15 178)' }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-bold text-[oklch(0.48_0.035_255)]">Exercise</p>
              <div className="mt-1 h-16 rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
                <div className="flex h-full items-end gap-[2px]">
                  {exerciseData.slice(-24).map((m, i) => (
                    <div key={i} className="flex-1 rounded-t-sm" style={{ height: `${Math.min((m.value / 120) * 100, 100)}%`, backgroundColor: 'oklch(0.72 0.15 178)' }} />
                  ))}
                </div>
              </div>
            </div>
            <div>
              <p className="text-sm font-bold text-[oklch(0.48_0.035_255)]">Sleep</p>
              <div className="mt-1 h-16 rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
                <div className="flex h-full items-end gap-[2px]">
                  {sleepData.slice(-14).map((m, i) => (
                    <div key={i} className="flex-1 rounded-t-sm" style={{ height: `${Math.min((m.value / 12) * 100, 100)}%`, backgroundColor: 'oklch(0.56 0.19 292)' }} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}
