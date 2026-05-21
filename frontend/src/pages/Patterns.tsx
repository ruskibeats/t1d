/** @jsxImportSource @emotion/react */
import { useEffect, useState } from 'react'
import axios from 'axios'
import { CheckCircle2, Dumbbell, Moon, RefreshCw, Utensils, AlertTriangle, Clock } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

const emptyPatternAnalysis = {
  analysis: { grade: '—', tir: { percentage: 0, below_range: { percentage: 0 }, above_range: { percentage: 0 } }, estimated_a1c: null },
  statistics: { average: 0, min_value: null, max_value: null, std_dev: null, total_readings: 0 },
}

type SignalLevel = 'good' | 'watch' | 'attention'

function getSignalLevel(grade: string): SignalLevel {
  if (['A', 'B'].includes(grade)) return 'good'
  if (['C'].includes(grade)) return 'watch'
  if (['D', 'F'].includes(grade)) return 'attention'
  return 'good'
}

function getSignalMeta(level: SignalLevel) {
  switch (level) {
    case 'good':
      return {
        label: 'Good',
        icon: CheckCircle2,
        color: 'text-[oklch(0.43_0.13_178)]',
        bg: 'bg-[oklch(0.72_0.15_178/0.1)]',
        border: 'border-[oklch(0.72_0.15_178/0.2)]',
        description: 'Your glucose has been stable. Keep doing what you are doing.',
      }
    case 'watch':
      return {
        label: 'Worth watching',
        icon: Clock,
        color: 'text-[oklch(0.52_0.12_73)]',
        bg: 'bg-[oklch(0.85_0.12_85/0.1)]',
        border: 'border-[oklch(0.85_0.12_85/0.2)]',
        description: 'Some patterns are emerging. Nothing urgent, but worth keeping an eye on.',
      }
    case 'attention':
      return {
        label: 'Needs attention',
        icon: AlertTriangle,
        color: 'text-[oklch(0.52_0.16_27)]',
        bg: 'bg-[oklch(0.76_0.15_72/0.1)]',
        border: 'border-[oklch(0.76_0.15_72/0.2)]',
        description: 'A few patterns stand out. Consider discussing with your diabetes team.',
      }
  }
}

export function PatternsPage() {
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState<any>(emptyPatternAnalysis)
  const [spikes, setSpikes] = useState<any[]>([])
  const [overnight, setOvernight] = useState<any[]>([])
  const [exercise, setExercise] = useState<any[]>([])

  const runAnalysis = async () => {
    setLoading(true)
    try {
      const [analysisRes, spikesRes, overnightRes, exerciseRes] = await Promise.all([
        axios.post('/api/v1/patterns/analyze', {
          pattern_type: 'time_in_range',
          time_period: 'weekly',
          start_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          end_date: new Date().toISOString(),
        }),
        axios.post('/api/v1/patterns/spikes', { min_carbs: 30 }),
        axios.post('/api/v1/patterns/overnight'),
        axios.post('/api/v1/patterns/exercise'),
      ])
      setAnalysis(analysisRes.data ?? emptyPatternAnalysis)
      setSpikes(spikesRes.data?.spikes ?? [])
      setOvernight(overnightRes.data?.events ?? [])
      setExercise(exerciseRes.data?.impacts ?? [])
    } catch {
      console.info('Pattern API unavailable or no records yet.')
      setAnalysis(emptyPatternAnalysis)
      setSpikes([])
      setOvernight([])
      setExercise([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { runAnalysis() }, [])

  const tir = analysis?.analysis?.tir ?? emptyPatternAnalysis.analysis.tir
  const statistics = analysis?.statistics ?? emptyPatternAnalysis.statistics
  const grade = analysis?.analysis?.grade ?? '—'
  const signalLevel = getSignalLevel(grade)
  const signal = getSignalMeta(signalLevel)
  const SignalIcon = signal.icon

  return (
    <div className="page-shell space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="kicker"><span className="kicker-dot" /> Pattern analysis</div>
          <h1 className="mt-2 text-3xl font-black tracking-[-0.06em] text-[oklch(0.22_0.04_255)]">Your patterns</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[oklch(0.48_0.035_255)]">
            Plain-English signals from your glucose, meals, activity, and sleep.
          </p>
        </div>
        <Button onClick={runAnalysis} disabled={loading}>
          <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          {loading ? 'Analysing' : 'Refresh'}
        </Button>
      </div>

      {/* Main signal card */}
      <Card className={cn('p-6', signal.bg, signal.border, 'border')}>
        <div className="flex items-start gap-4">
          <div className={cn('grid h-14 w-14 place-items-center rounded-2xl', signal.bg)}>
            <SignalIcon className={cn('h-7 w-7', signal.color)} />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <span className={cn('text-2xl font-black', signal.color)}>{signal.label}</span>
              <span className="text-sm font-semibold text-[oklch(0.48_0.035_255)]">Grade {grade}</span>
            </div>
            <p className="mt-2 text-sm leading-6 text-[oklch(0.36_0.035_255)]">{signal.description}</p>
            <div className="mt-4 grid grid-cols-3 gap-3">
              <div className="rounded-xl bg-white/60 p-3 text-center">
                <p className="text-2xl font-black text-[oklch(0.24_0.04_255)]">{tir.percentage.toFixed(0)}%</p>
                <p className="text-[0.65rem] font-bold text-[oklch(0.48_0.035_255)]">In range</p>
              </div>
              <div className="rounded-xl bg-white/60 p-3 text-center">
                <p className="text-2xl font-black text-[oklch(0.24_0.04_255)]">{statistics.average.toFixed(0)}</p>
                <p className="text-[0.65rem] font-bold text-[oklch(0.48_0.035_255)]">Avg mg/dL</p>
              </div>
              <div className="rounded-xl bg-white/60 p-3 text-center">
                <p className="text-2xl font-black text-[oklch(0.24_0.04_255)]">{analysis?.analysis?.estimated_a1c ?? '—'}</p>
                <p className="text-[0.65rem] font-bold text-[oklch(0.48_0.035_255)]">Est. A1C</p>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Pattern cards grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Meals card */}
        <Card className="p-5">
          <div className="mb-3 flex items-center gap-2">
            <Utensils className="h-5 w-5 text-[oklch(0.52_0.12_73)]" />
            <h3 className="font-black tracking-[-0.02em]">Meals</h3>
          </div>
          {spikes.length === 0 ? (
            <p className="text-sm text-[oklch(0.48_0.035_255)]">No notable meal spikes this week.</p>
          ) : (
            <div className="space-y-2">
              {spikes.slice(0, 3).map((spike, i) => (
                <div key={i} className="rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-bold">{spike.meal.food_name}</p>
                    <span className={cn(
                      'rounded-full px-2 py-0.5 text-[0.65rem] font-black uppercase',
                      spike.severity === 'high' ? 'bg-[oklch(0.76_0.15_72/0.15)] text-[oklch(0.52_0.16_27)]' :
                      spike.severity === 'moderate' ? 'bg-[oklch(0.85_0.12_85/0.15)] text-[oklch(0.52_0.12_73)]' :
                      'bg-[oklch(0.72_0.15_178/0.12)] text-[oklch(0.43_0.13_178)]'
                    )}>{spike.severity}</span>
                  </div>
                  <p className="mt-1 text-xs text-[oklch(0.48_0.035_255)]">+{spike.glucose_rise} mg/dL to {spike.peak_value}</p>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Exercise card */}
        <Card className="p-5">
          <div className="mb-3 flex items-center gap-2">
            <Dumbbell className="h-5 w-5 text-[oklch(0.43_0.13_178)]" />
            <h3 className="font-black tracking-[-0.02em]">Exercise</h3>
          </div>
          {exercise.length === 0 ? (
            <p className="text-sm text-[oklch(0.48_0.035_255)]">No exercise logged this week.</p>
          ) : (
            <div className="space-y-2">
              {exercise.slice(0, 3).map((impact, i) => (
                <div key={i} className="rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
                  <p className="text-sm font-bold capitalize">{impact.exercise.intensity} {impact.exercise.exercise_type || 'exercise'}</p>
                  <p className="mt-1 text-xs text-[oklch(0.48_0.035_255)]">
                    {impact.exercise.duration_minutes} min · {impact.impact.avg_change_from_baseline > 0 ? '+' : ''}{impact.impact.avg_change_from_baseline.toFixed(0)} mg/dL
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Overnight card */}
        <Card className="p-5">
          <div className="mb-3 flex items-center gap-2">
            <Moon className="h-5 w-5 text-[oklch(0.46_0.15_255)]" />
            <h3 className="font-black tracking-[-0.02em]">Overnight</h3>
          </div>
          {overnight.length === 0 ? (
            <div className="flex items-center gap-2 rounded-xl bg-[oklch(0.72_0.15_178/0.08)] p-3">
              <CheckCircle2 className="h-4 w-4 text-[oklch(0.43_0.13_178)]" />
              <p className="text-sm font-semibold text-[oklch(0.43_0.13_178)]">No overnight lows this week.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {overnight.slice(0, 3).map((event, i) => (
                <div key={i} className="rounded-xl bg-[oklch(0.76_0.15_72/0.08)] p-3">
                  <p className="text-sm font-bold">{new Date(event.date).toDateString()}</p>
                  <p className="mt-1 text-xs text-[oklch(0.48_0.035_255)]">Low: {event.lowest_value} mg/dL · {event.percentage_of_night.toFixed(1)}% of night</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Full statistics */}
      <Card className="p-5">
        <h3 className="mb-4 font-black tracking-[-0.02em]">Weekly statistics</h3>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            ['Average', `${statistics.average.toFixed(0)} mg/dL`],
            ['Low / high', `${statistics.min_value.toFixed(0)} / ${statistics.max_value.toFixed(0)}`],
            ['Variability', statistics.std_dev?.toFixed(1) ?? '—'],
            ['Readings', statistics.total_readings ?? '—'],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
              <p className="text-[0.65rem] font-black uppercase tracking-[0.1em] text-[oklch(0.48_0.035_255)]">{label}</p>
              <p className="mt-1 text-lg font-black text-[oklch(0.24_0.04_255)]">{value}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

export default PatternsPage
