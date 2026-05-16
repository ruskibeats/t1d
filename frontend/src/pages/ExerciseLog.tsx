/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Activity, Timer, Flame, Plus } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { StatCard } from '@/components/ui/StatCard'
import { useExercise } from '@/hooks/useExercise'
import { cn } from '@/lib/utils'

const activityTypes = ['running', 'cycling', 'walking', 'swimming', 'weightlifting', 'yoga', 'hiit', 'other']
const intensities = ['low', 'moderate', 'high'] as const

export function ExerciseLogPage() {
  const { entries, createEntry } = useExercise()
  const [type, setType] = useState('running')
  const [duration, setDuration] = useState(30)
  const [intensity, setIntensity] = useState<typeof intensities[number]>('moderate')
  const [calories, setCalories] = useState(0)
  const [showForm, setShowForm] = useState(false)

  const handleSubmit = async () => {
    await createEntry({
      type, duration_minutes: duration, intensity,
      calories: calories || undefined,
      start_time: new Date().toISOString(), source: 'manual',
    })
    setShowForm(false)
  }

  const weeklyMinutes = entries.reduce((s, e) => s + e.duration_minutes, 0)
  const weeklyCalories = entries.reduce((s, e) => s + (e.calories || 0), 0)

  return (
    <div className="page-shell space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="kicker"><span className="kicker-dot" /> Physical activity</div>
          <h2 className="mt-2 text-2xl font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">Exercise log</h2>
        </div>
        <Button onClick={() => setShowForm(!showForm)}><Plus className="h-4 w-4" /> Log exercise</Button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <StatCard title="Weekly total" value={`${weeklyMinutes}`} subtitle="minutes" icon={Timer} variant="success" />
        <StatCard title="Calories burned" value={`${weeklyCalories.toFixed(0)}`} subtitle="kcal" icon={Flame} variant="default" />
      </div>

      {showForm && (
        <Card className="p-5 space-y-4">
          <h3 className="font-black">New exercise entry</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Type</label>
              <select value={type} onChange={e => setType(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm">
                {activityTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Duration (min)</label>
              <input type="number" value={duration} min={1} onChange={e => setDuration(parseInt(e.target.value) || 30)}
                className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Intensity</label>
              <div className="mt-1 flex gap-1">
                {intensities.map(i => (
                  <button key={i} onClick={() => setIntensity(i)}
                    className={cn('flex-1 rounded-lg px-2 py-1.5 text-xs font-bold transition',
                      intensity === i ? 'bg-[oklch(0.23_0.045_255)] text-white' : 'bg-[oklch(0.94_0.03_245)] text-[oklch(0.45_0.035_255)]')}>
                    {i}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Calories (optional)</label>
              <input type="number" value={calories || ''} min={0} onChange={e => setCalories(parseInt(e.target.value) || 0)}
                className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm" />
            </div>
          </div>
          <Button onClick={handleSubmit}><Plus className="h-4 w-4" /> Save</Button>
        </Card>
      )}

      <Card className="p-5">
        <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">Recent sessions</h3>
        <div className="space-y-3">
          {entries.map(entry => (
            <div key={entry.id} className="flex items-center justify-between rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
              <div className="flex items-center gap-3">
                <div className="grid h-8 w-8 place-items-center rounded-lg bg-[oklch(0.72_0.15_178/0.15)]">
                  <Activity className="h-4 w-4 text-[oklch(0.48_0.12_255)]" />
                </div>
                <div>
                  <p className="font-bold text-sm capitalize">{entry.type}</p>
                  <p className="text-xs text-[oklch(0.48_0.035_255)]">
                    {entry.duration_minutes}min · {entry.intensity || 'moderate'}
                    {entry.calories && ` · ${entry.calories} kcal`}
                  </p>
                </div>
              </div>
              <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-bold uppercase',
                entry.intensity === 'high' ? 'bg-[oklch(0.76_0.15_72/0.15)] text-[oklch(0.65_0.15_72)]' :
                entry.intensity === 'low' ? 'bg-[oklch(0.72_0.15_178/0.12)] text-[oklch(0.55_0.15_178)]' :
                'bg-[oklch(0.6_0.12_245/0.12)] text-[oklch(0.5_0.12_245)]')}>
                {entry.intensity || 'moderate'}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
