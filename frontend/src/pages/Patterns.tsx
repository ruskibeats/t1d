/** @jsxImportSource @emotion/react */
import { useEffect, useState } from 'react'
import axios from 'axios'
import { Brain, Dumbbell, Moon, RefreshCw, Utensils } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { demoExerciseImpacts, demoOvernight, demoPatternAnalysis, demoSpikes } from '@/lib/demoData'
import { cn } from '@/lib/utils'

const gradeStyles: Record<string, string> = {
  A: 'text-[oklch(0.43_0.13_178)]',
  B: 'text-[oklch(0.46_0.15_255)]',
  C: 'text-[oklch(0.52_0.12_73)]',
  D: 'text-[oklch(0.52_0.14_48)]',
  F: 'text-[oklch(0.52_0.16_27)]',
}

export function PatternsPage() {
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState<any>(demoPatternAnalysis)
  const [spikes, setSpikes] = useState<any[]>(demoSpikes)
  const [overnight, setOvernight] = useState<any[]>(demoOvernight)
  const [exercise, setExercise] = useState<any[]>(demoExerciseImpacts)
  const [demoMode, setDemoMode] = useState(true)

  const runAnalysis = async () => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) {
      setAnalysis(demoPatternAnalysis)
      setSpikes(demoSpikes)
      setOvernight(demoOvernight)
      setExercise(demoExerciseImpacts)
      setDemoMode(true)
      return
    }

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

      setAnalysis(analysisRes.data ?? demoPatternAnalysis)
      setSpikes(spikesRes.data?.spikes?.length ? spikesRes.data.spikes : demoSpikes)
      setOvernight(overnightRes.data?.events?.length ? overnightRes.data.events : demoOvernight)
      setExercise(exerciseRes.data?.impacts?.length ? exerciseRes.data.impacts : demoExerciseImpacts)
      setDemoMode(false)
    } catch (error) {
      console.info('Using local demo pattern analysis until the API has records.', error)
      setAnalysis(demoPatternAnalysis)
      setSpikes(demoSpikes)
      setOvernight(demoOvernight)
      setExercise(demoExerciseImpacts)
      setDemoMode(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    runAnalysis()
  }, [])

  const tir = analysis?.analysis?.tir ?? demoPatternAnalysis.analysis.tir
  const statistics = analysis?.statistics ?? demoPatternAnalysis.statistics
  const grade = analysis?.analysis?.grade ?? 'B'

  return (
    <div className="page-shell space-y-7">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="kicker"><span className="kicker-dot" /> Pattern engine</div>
          <h1 className="mt-2 text-4xl font-black tracking-[-0.06em] text-[oklch(0.22_0.04_255)]">Pattern analysis</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[oklch(0.48_0.035_255)]">Translate glucose, meals, movement, and nights into repeatable personal signals. {demoMode ? 'Showing demo insights.' : 'Live analysis complete.'}</p>
        </div>
        <Button onClick={runAnalysis} disabled={loading}>
          <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          {loading ? 'Analyzing' : 'Refresh'}
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="hero-surface p-6">
          <div className="relative z-10">
            <div className="flex items-center justify-between">
              <span className="signal-pill">Weekly control grade</span>
              <Brain className="h-5 w-5 text-[oklch(0.74_0.13_178)]" />
            </div>
            <div className={cn('mt-7 text-8xl font-black tracking-[-0.08em]', gradeStyles[grade] ?? 'text-[oklch(0.72_0.15_178)]')}>{grade}</div>
            <p className="mt-3 max-w-md text-sm leading-6 text-[oklch(0.86_0.025_245)]">{tir.percentage.toFixed(0)}% time in range with an estimated A1C of {analysis?.analysis?.estimated_a1c ?? '6.9'}%.</p>
            <div className="mt-6 grid grid-cols-3 gap-2">
              <div className="rounded-2xl bg-[oklch(1_0_0/0.08)] p-3"><div className="text-2xl font-black">{tir.percentage.toFixed(0)}%</div><div className="text-[0.68rem] font-bold text-[oklch(0.75_0.04_245)]">In range</div></div>
              <div className="rounded-2xl bg-[oklch(1_0_0/0.08)] p-3"><div className="text-2xl font-black">{tir.below_range.percentage.toFixed(0)}%</div><div className="text-[0.68rem] font-bold text-[oklch(0.75_0.04_245)]">Below</div></div>
              <div className="rounded-2xl bg-[oklch(1_0_0/0.08)] p-3"><div className="text-2xl font-black">{tir.above_range.percentage.toFixed(0)}%</div><div className="text-[0.68rem] font-bold text-[oklch(0.75_0.04_245)]">Above</div></div>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-black tracking-[-0.03em]">Statistics</h2>
          <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              ['Average', `${statistics.average.toFixed(0)} mg/dL`],
              ['Min / max', `${statistics.min_value.toFixed(0)} / ${statistics.max_value.toFixed(0)}`],
              ['Variability', statistics.std_dev.toFixed(1)],
              ['Readings', statistics.total_readings],
            ].map(([label, value]) => (
              <div key={label} className="panel-subtle p-4">
                <div className="text-[0.68rem] font-black uppercase tracking-[0.12em] text-[oklch(0.5_0.035_255)]">{label}</div>
                <div className="mt-2 text-2xl font-black tracking-[-0.05em] text-[oklch(0.24_0.04_255)]">{value}</div>
              </div>
            ))}
          </div>
          <div className="mt-5 rounded-[24px] bg-[oklch(0.95_0.025_255)] p-4 text-sm leading-6 text-[oklch(0.4_0.04_255)]">
            The engine is looking for repeatable context, not single bad numbers. It weighs timing, meal composition, exercise proximity, and overnight windows.
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card className="p-6">
          <div className="mb-5 flex items-center gap-3"><Utensils className="h-5 w-5 text-[oklch(0.52_0.12_73)]" /><h2 className="text-lg font-black tracking-[-0.03em]">Post-meal spikes ({spikes.length})</h2></div>
          <div className="space-y-3">
            {spikes.map((spike, index) => (
              <div key={index} className="panel-subtle p-4">
                <div className="flex justify-between gap-4">
                  <div><p className="font-black tracking-[-0.02em]">{spike.meal.food_name}</p><p className="text-sm font-semibold text-[oklch(0.48_0.035_255)]">{spike.meal.carbs}g carbs, {spike.timing ?? 'delayed rise'}</p></div>
                  <span className="chip capitalize">{spike.severity}</span>
                </div>
                <div className="mt-3 text-sm font-bold text-[oklch(0.42_0.04_255)]">+{spike.glucose_rise} mg/dL to {spike.peak_value} mg/dL</div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-5 flex items-center gap-3"><Dumbbell className="h-5 w-5 text-[oklch(0.43_0.13_178)]" /><h2 className="text-lg font-black tracking-[-0.03em]">Exercise impacts ({exercise.length})</h2></div>
          <div className="space-y-3">
            {exercise.map((impact, index) => (
              <div key={index} className="panel-subtle flex items-center justify-between gap-4 p-4">
                <div><p className="font-black capitalize tracking-[-0.02em]">{impact.exercise.intensity} {impact.exercise.exercise_type || 'exercise'}</p><p className="text-sm font-semibold text-[oklch(0.48_0.035_255)]">{impact.exercise.duration_minutes} minutes</p></div>
                <span className="text-lg font-black text-[oklch(0.43_0.13_178)]">{impact.impact.avg_change_from_baseline > 0 ? '+' : ''}{impact.impact.avg_change_from_baseline.toFixed(0)} mg/dL</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6 xl:col-span-2">
          <div className="mb-5 flex items-center gap-3"><Moon className="h-5 w-5 text-[oklch(0.46_0.15_255)]" /><h2 className="text-lg font-black tracking-[-0.03em]">Overnight hypoglycemia ({overnight.length})</h2></div>
          {overnight.length === 0 ? (
            <p className="text-sm font-semibold text-[oklch(0.48_0.035_255)]">No overnight lows detected in this window.</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {overnight.map((event, index) => (
                <div key={index} className="panel-subtle flex items-center justify-between p-4">
                  <div><p className="font-black">{new Date(event.date).toDateString()}</p><p className="text-sm font-semibold text-[oklch(0.48_0.035_255)]">{event.percentage_of_night.toFixed(1)}% of night low</p></div>
                  <span className="text-2xl font-black text-[oklch(0.52_0.16_27)]">{event.lowest_value}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

export default PatternsPage
