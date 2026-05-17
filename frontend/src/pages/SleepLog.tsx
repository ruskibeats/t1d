/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Moon, Star, Plus } from 'lucide-react'
import { format } from 'date-fns'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { StatCard } from '@/components/ui/StatCard'
import { useSleep } from '@/hooks/useSleep'
import { cn } from '@/lib/utils'

export function SleepLogPage() {
  const { entries, createEntry } = useSleep()
  const [bedtime, setBedtime] = useState('')
  const [waketime, setWaketime] = useState('')
  const [score, setScore] = useState(7)
  const [showForm, setShowForm] = useState(false)

  const avgDuration = entries.length
    ? (entries.reduce((s, e) => s + (e.duration_minutes || 0), 0) / entries.length / 60).toFixed(1)
    : '--'
  const avgScore = entries.length
    ? (entries.reduce((s, e) => s + (e.score || 0), 0) / entries.length).toFixed(0)
    : '--'

  const handleSubmit = async () => {
    if (!bedtime || !waketime) return
    const start = new Date(bedtime).toISOString()
    const end = new Date(waketime).toISOString()
    const duration = (new Date(end).getTime() - new Date(start).getTime()) / 60000
    await createEntry({
      start_time: start, end_time: end, duration_minutes: duration,
      score, source: 'manual',
    })
    setShowForm(false)
  }

  return (
    <div className="page-shell space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="kicker"><span className="kicker-dot" /> Rest & recovery</div>
          <h2 className="mt-2 text-2xl font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">Sleep log</h2>
        </div>
        <Button onClick={() => setShowForm(!showForm)}><Plus className="h-4 w-4" /> Log sleep</Button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <StatCard title="Avg duration" value={avgDuration as string} subtitle="hours" icon={Moon} variant="default" />
        <StatCard title="Avg quality" value={avgScore as string} subtitle="/10" icon={Star} variant={parseInt(avgScore as string) >= 7 ? 'success' : 'warning'} />
      </div>

      {entries.length > 0 && entries.some((e: any) => e.deep_minutes || e.light_minutes || e.rem_minutes || e.awake_minutes) && (
        <Card className="p-5">
          <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">Sleep stages (latest)</h3>
          <div className="grid grid-cols-4 gap-3">
            {['deep', 'rem', 'light', 'awake'].map(stage => {
              const latest = entries.find((e: any) => (e as any)[`${stage}_minutes`])
              const val = latest ? (latest as any)[`${stage}_minutes`] : 0
              return <div key={stage} className="rounded-xl bg-[oklch(0.96_0.02_245)] p-3 text-center">
                <p className="text-2xl font-black">{val}m</p>
                <p className="text-xs font-bold capitalize">{stage}</p>
              </div>
            })}
          </div>
        </Card>
      )}

      {showForm && (
        <Card className="p-5 space-y-4">
          <h3 className="font-black">Log sleep entry</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Bedtime</label>
              <input type="datetime-local" value={bedtime} onChange={e => setBedtime(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Wake time</label>
              <input type="datetime-local" value={waketime} onChange={e => setWaketime(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm" />
            </div>
          </div>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Quality score: {score}/10</label>
            <input type="range" min={1} max={10} value={score} onChange={e => setScore(parseInt(e.target.value))}
              className="mt-2 w-full" />
            <div className="flex justify-between text-[10px] text-[oklch(0.55_0.03_245)]">
              <span>Poor</span><span>Excellent</span>
            </div>
          </div>
          <Button onClick={handleSubmit}><Plus className="h-4 w-4" /> Save</Button>
        </Card>
      )}

      <Card className="p-5">
        <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">Sleep history</h3>
        <div className="space-y-3">
          {entries.map(entry => {
            const durHours = entry.duration_minutes ? (entry.duration_minutes / 60).toFixed(1) : '--'
            return (
              <div key={entry.id} className="flex items-center justify-between rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
                <div className="flex items-center gap-3">
                  <div className="grid h-8 w-8 place-items-center rounded-lg bg-[oklch(0.56_0.19_292/0.15)]">
                    <Moon className="h-4 w-4 text-[oklch(0.56_0.19_292)]" />
                  </div>
                  <div>
                    <p className="font-bold text-sm">{durHours}h sleep</p>
                    <p className="text-xs text-[oklch(0.48_0.035_255)]">{format(new Date(entry.start_time), 'MMM d, h:mm a')}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {entry.score && (
                    <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-bold',
                      entry.score >= 7 ? 'bg-[oklch(0.72_0.15_178/0.15)] text-[oklch(0.55_0.15_178)]' :
                      entry.score >= 4 ? 'bg-[oklch(0.76_0.15_72/0.15)] text-[oklch(0.65_0.15_72)]' :
                      'bg-[oklch(0.72_0.18_27/0.15)] text-[oklch(0.65_0.18_27)]')}>
                      {entry.score}/10
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}
