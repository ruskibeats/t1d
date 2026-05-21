/** @jsxImportSource @emotion/react */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, AlertTriangle, Brain, Clock3, Droplets, Moon, Plus, ShieldCheck, Sparkles, TrendingDownIcon, TrendingUpIcon, Utensils } from 'lucide-react'
import { format } from 'date-fns'
import { Card } from '@/components/ui/Card'
import { StatCard } from '@/components/ui/StatCard'
import { Button } from '@/components/ui/Button'
import { RecentEvents } from '@/components/dashboard/RecentEvents'
import { QuickLog } from '@/components/dashboard/QuickLog'
import { GlucoseChart } from '@/components/charts/GlucoseChart'
import { useGlucose } from '@/hooks/useGlucose'
import { useEvents } from '@/hooks/useEvents'
import { useInsights } from '@/hooks/useInsights'
import { cn } from '@/lib/utils'

const ranges = [
  { label: '1D', value: '1d' },
  { label: '3D', value: '3d' },
  { label: '7D', value: '7d' },
  { label: '14D', value: '14d' },
] as const

const severityColors: Record<string, string> = {
  low: 'bg-[oklch(0.72_0.15_178/0.18)] text-[oklch(0.86_0.11_178)]',
  moderate: 'bg-[oklch(0.85_0.12_85/0.18)] text-[oklch(0.85_0.12_85)]',
  high: 'bg-[oklch(0.76_0.15_72/0.18)] text-[oklch(0.86_0.12_72)]',
}

const patternIcons: Record<string, typeof Utensils> = {
  time_of_day_spike: Clock3,
  time_of_day_low: Moon,
  meal_spike: Utensils,
  trend: Activity,
  positive: Sparkles,
}

interface InsightItem {
  type: string
  severity: string
  description: string
  recommendation?: string
  [key: string]: any
}

export function Dashboard() {
  const navigate = useNavigate()
  const { readings, stats, demoMode, fetchReadings } = useGlucose()
  const { events, loading: eventsLoading } = useEvents()
  const { insights, loading: insightsLoading, predictMeal } = useInsights()
  const [timeRange, setTimeRange] = useState<'1d' | '3d' | '7d' | '14d'>('3d')
  const [showPreMeal, setShowPreMeal] = useState(false)
  const [preMealFood, setPreMealFood] = useState('')
  const [preMealResult, setPreMealResult] = useState<any>(null)
  const [preMealLoading, setPreMealLoading] = useState(false)

  useEffect(() => {
    fetchReadings(timeRange)
  }, [timeRange, fetchReadings])

  const latestReading = readings[0]
  const trend = readings.length >= 2 ? readings[0].glucose_value - readings[1].glucose_value : 0
  const status = !latestReading ? 'no data' : latestReading.glucose_value < 70 ? 'low' : latestReading.glucose_value > 180 ? 'high' : 'in range'

  const allInsights: InsightItem[] = [
    ...(insights?.time_of_day_patterns || []),
    ...(insights?.meal_patterns || []),
  ]

  const handlePreMeal = async () => {
    if (!preMealFood.trim()) return
    setPreMealLoading(true)
    const result = await predictMeal(preMealFood.trim(), latestReading?.glucose_value)
    setPreMealResult(result)
    setPreMealLoading(false)
  }

  return (
    <div className="page-shell space-y-7">
      <section className="hero-surface p-6 md:p-8 lg:p-9">
        <div className="relative z-10 grid gap-8 xl:grid-cols-[1.05fr_0.95fr] xl:items-end">
          <div className="max-w-3xl">
            <div className="mb-5 flex flex-wrap items-center gap-2">
              <span className="signal-pill"><span className="mr-2 inline-block h-2 w-2 animate-breathe rounded-full bg-[oklch(0.72_0.15_178)]" />Service running</span>
              {demoMode && <span className="signal-pill">Demo data active</span>}
              <span className="signal-pill">Updated {format(new Date(), 'h:mm a')}</span>
            </div>
            <h1 className="max-w-2xl text-4xl font-black leading-[0.95] tracking-[-0.065em] md:text-6xl">
              See the rhythm behind the numbers.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[oklch(0.86_0.025_245)] md:text-lg">
              Track your glucose, meals, and patterns. Get plain-English insights from your data.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Button size="lg" className="bg-[oklch(0.72_0.15_178)] text-[oklch(0.18_0.04_255)] hover:bg-[oklch(0.78_0.14_178)]" onClick={() => setShowPreMeal(true)}>
                <Utensils className="h-4 w-4" /> About to eat
              </Button>
              <Button size="lg" variant="outline" className="border-[oklch(1_0_0/0.16)] bg-[oklch(1_0_0/0.08)] text-[oklch(0.96_0.012_245)] hover:bg-[oklch(1_0_0/0.13)]" onClick={() => navigate('/events')}>
                <Plus className="h-4 w-4" /> Log event
              </Button>
              <Button size="lg" variant="outline" className="border-[oklch(1_0_0/0.16)] bg-[oklch(1_0_0/0.08)] text-[oklch(0.96_0.012_245)] hover:bg-[oklch(1_0_0/0.13)]" onClick={() => navigate('/chat')}>
                <Brain className="h-4 w-4" /> Ask AI
              </Button>
            </div>
          </div>

          <div className="grid gap-3 rounded-[30px] border border-[oklch(1_0_0/0.12)] bg-[oklch(1_0_0/0.08)] p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase tracking-[0.14em] text-[oklch(0.78_0.06_245)]">Current signal</span>
              <span className={cn('rounded-full px-2.5 py-1 text-xs font-black capitalize', status === 'in range' ? 'bg-[oklch(0.72_0.15_178/0.18)] text-[oklch(0.86_0.11_178)]' : 'bg-[oklch(0.76_0.15_72/0.18)] text-[oklch(0.86_0.12_72)]')}>{status}</span>
            </div>
            <div className="flex items-end justify-between gap-4">
              <div>
                <div className="text-6xl font-black tracking-[-0.08em] md:text-7xl">{latestReading?.glucose_value ?? '--'}</div>
                <div className="mt-1 text-sm font-bold text-[oklch(0.76_0.04_245)]">mg/dL from {latestReading?.source ?? 'sensor'}</div>
              </div>
              <div className="pb-2 text-right">
                <div className={cn('text-2xl font-black', trend > 0 ? 'text-[oklch(0.8_0.13_27)]' : trend < 0 ? 'text-[oklch(0.78_0.13_178)]' : 'text-[oklch(0.8_0.04_245)]')}>
                  {trend > 0 ? '+' : ''}{trend.toFixed(0)}
                </div>
                <div className="text-xs font-semibold text-[oklch(0.7_0.035_245)]">since previous</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {showPreMeal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="w-full max-w-lg p-6">
            <h2 className="text-xl font-black tracking-[-0.03em]">What are you about to eat?</h2>
            <p className="mt-2 text-sm text-[oklch(0.48_0.035_255)]">I'll analyze your history with this food and give you personalized insights.</p>
            <div className="mt-4 flex gap-2">
              <input
                type="text"
                value={preMealFood}
                onChange={(e) => setPreMealFood(e.target.value)}
                placeholder="e.g. pizza, pasta, sandwich..."
                className="flex-1 rounded-xl border border-[oklch(0.86_0.02_250)] bg-[oklch(0.98_0.01_245)] px-4 py-3 text-sm font-medium outline-none focus:border-[oklch(0.72_0.15_178)]"
                onKeyDown={(e) => e.key === 'Enter' && handlePreMeal()}
              />
              <Button onClick={handlePreMeal} disabled={preMealLoading || !preMealFood.trim()}>
                {preMealLoading ? 'Analyzing...' : 'Analyze'}
              </Button>
            </div>
            {preMealResult && (
              <div className="mt-4 space-y-3">
                <div className="rounded-xl bg-[oklch(0.94_0.03_245)] p-4">
                  <p className="text-sm font-medium leading-6 text-[oklch(0.24_0.04_255)]">{preMealResult.prediction || preMealResult.message}</p>
                </div>
                {preMealResult.current_status && (
                  <div className="rounded-xl bg-[oklch(0.72_0.15_178/0.1)] p-4">
                    <p className="text-sm font-medium leading-6 text-[oklch(0.24_0.04_255)]">{preMealResult.current_status}</p>
                  </div>
                )}
                {preMealResult.tips && preMealResult.tips.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-black uppercase tracking-[0.14em] text-[oklch(0.48_0.035_255)]">Tips</p>
                    {preMealResult.tips.map((tip: string, i: number) => (
                      <div key={i} className="flex gap-2 text-sm text-[oklch(0.44_0.035_255)]">
                        <span className="text-[oklch(0.72_0.15_178)]">•</span>
                        <span>{tip}</span>
                      </div>
                    ))}
                  </div>
                )}
                {preMealResult.recommendation && (
                  <div className="rounded-xl border border-[oklch(0.86_0.02_250)] p-4">
                    <p className="text-sm leading-6 text-[oklch(0.44_0.035_255)]">{preMealResult.recommendation}</p>
                  </div>
                )}
                <p className="text-xs italic text-[oklch(0.48_0.035_255)]">{preMealResult.disclaimer}</p>
              </div>
            )}
            <div className="mt-4 flex justify-end">
              <Button variant="outline" onClick={() => { setShowPreMeal(false); setPreMealFood(''); setPreMealResult(null); }}>Close</Button>
            </div>
          </Card>
        </div>
      )}

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="kicker"><span className="kicker-dot" /> Live dashboard</div>
          <h2 className="mt-2 text-2xl font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">Personal pattern cockpit</h2>
        </div>
        <div className="flex w-full rounded-2xl border border-[oklch(0.86_0.02_250)] bg-[oklch(0.98_0.01_245/0.72)] p-1 md:w-auto">
          {ranges.map((range) => (
            <button
              key={range.value}
              className={cn('flex-1 rounded-xl px-4 py-2 text-sm font-black transition md:flex-none', timeRange === range.value ? 'bg-[oklch(0.23_0.045_255)] text-[oklch(0.97_0.01_245)] shadow-lg' : 'text-[oklch(0.45_0.035_255)] hover:bg-[oklch(0.93_0.018_245)]')}
              onClick={() => setTimeRange(range.value)}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard title="Current glucose" value={latestReading ? `${latestReading.glucose_value}` : '--'} subtitle="mg/dL" trend={trend > 0 ? 'up' : trend < 0 ? 'down' : 'stable'} trendValue={Math.abs(trend)} icon={Droplets} variant={latestReading ? latestReading.glucose_value < 70 ? 'danger' : latestReading.glucose_value > 180 ? 'warning' : 'success' : 'default'} />
        <StatCard title="Time in range" value={stats?.time_in_range ? `${stats.time_in_range.percentage.toFixed(0)}%` : '--'} subtitle="Target 70 to 180" icon={TrendingUpIcon} variant="success" />
        <StatCard title="Below range" value={stats?.time_in_range ? `${stats.time_in_range.below_range.percentage.toFixed(0)}%` : '--'} subtitle="Under 70" icon={TrendingDownIcon} variant="danger" />
        <StatCard title="Above range" value={stats?.time_in_range ? `${stats.time_in_range.above_range.percentage.toFixed(0)}%` : '--'} subtitle="Over 180" icon={Clock3} variant="warning" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.6fr_0.8fr]">
        <Card className="overflow-hidden">
          <div className="flex flex-col gap-4 border-b border-[oklch(0.89_0.018_250)] p-5 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-lg font-black tracking-[-0.03em]">Glucose trace</h3>
              <p className="text-sm font-medium text-[oklch(0.48_0.035_255)]">Target band, excursions, and sensor cadence.</p>
            </div>
            <Button variant="outline" onClick={() => navigate('/glucose')}><Plus className="h-4 w-4" /> Add reading</Button>
          </div>
          <div className="p-3 md:p-5">
            <GlucoseChart readings={readings} timeRange={timeRange} />
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-black tracking-[-0.03em]">Quick log</h3>
              <Sparkles className="h-4 w-4 text-[oklch(0.56_0.19_292)]" />
            </div>
            <QuickLog />
          </Card>
          <Card className="p-5">
            <div className="mb-4 flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-[oklch(0.56_0.16_178)]" />
              <h3 className="text-lg font-black tracking-[-0.03em]">Safety boundary</h3>
            </div>
            <p className="text-sm leading-6 text-[oklch(0.44_0.035_255)]">The assistant explains patterns and escalates urgent language. It will not dose, diagnose, or replace clinical advice.</p>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card className="p-5">
          <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">Recent events</h3>
          <RecentEvents events={events} loading={eventsLoading} />
        </Card>

        <Card className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-black tracking-[-0.03em]">AI Insights</h3>
            {insightsLoading && <span className="text-xs text-[oklch(0.48_0.035_255)]">Analyzing...</span>}
          </div>
          <div className="space-y-3">
            {allInsights.length === 0 && !insightsLoading && (
              <p className="text-sm text-[oklch(0.48_0.035_255)]">
                Keep logging your meals and glucose data. The AI will detect patterns and share insights here.
              </p>
            )}
            {allInsights.map((insight, i) => {
              const Icon = patternIcons[insight.type] || AlertTriangle
              return (
                <div key={i} className="panel-subtle flex gap-3 p-4">
                  <div className={cn('grid h-10 w-10 shrink-0 place-items-center rounded-2xl', severityColors[insight.severity] || 'bg-[oklch(0.94_0.03_245)]')}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm leading-5 text-[oklch(0.36_0.035_255)]">{insight.description}</p>
                    {insight.recommendation && (
                      <p className="mt-2 text-xs leading-5 text-[oklch(0.44_0.035_255)]">{insight.recommendation}</p>
                    )}
                  </div>
                </div>
              )
            })}
            {typeof insights?.summary === 'string' && allInsights.length > 0 && (
              <div className="mt-2 rounded-xl bg-[oklch(0.72_0.15_178/0.08)] p-3">
                <p className="text-xs leading-5 text-[oklch(0.44_0.035_255)]">{insights.summary}</p>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}