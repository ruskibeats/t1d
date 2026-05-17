/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Timer, Plus, Calendar, Target, Zap } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useFasting } from '@/hooks/useFasting'

export function FastingLogPage() {
  const { entries, createEntry } = useFasting()
  const [showForm, setShowForm] = useState(false)
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [notes, setNotes] = useState('')

  const handleStartFast = async () => {
    if (!startTime) return
    await createEntry({
      start_time: new Date(startTime).toISOString(),
      end_time: endTime ? new Date(endTime).toISOString() : undefined,
      source: 'manual',
    })
    setShowForm(false)
    setStartTime('')
    setEndTime('')
    setNotes('')
  }

  // Calculate stats
  const completedFasts = entries.filter(e => e.end_time)
  const streak = completedFasts.length > 0 ? completedFasts.length : 0
  const longest = completedFasts.reduce((max, e) => Math.max(max, e.duration_minutes || 0), 0)
  const today = entries.some(e => e.start_time.startsWith(new Date().toISOString().split('T')[0]))

  return (
    <div className="page-shell space-y-6">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Fasting tracking</div>
        <h2 className="mt-2 text-2xl font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">Fasting log</h2>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="p-4 text-center">
          <Target className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{streak}</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Current streak</p>
        </Card>
        <Card className="p-4 text-center">
          <Zap className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{Math.round(longest / 60)}</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Longest (hrs)</p>
        </Card>
        <Card className="p-4 text-center">
          <Calendar className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{today ? 'Yes' : 'No'}</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Fasted today</p>
        </Card>
      </div>

      {/* Start/End Fast Button */}
      <Button onClick={() => setShowForm(true)} className="w-full">
        <Plus className="h-4 w-4" /> Start/End fast
      </Button>

      {/* Form Modal */}
      {showForm && (
        <Card className="p-5 space-y-4">
          <h3 className="font-black">Record fast</h3>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Start time</label>
            <input
              type="datetime-local"
              value={startTime}
              onChange={e => setStartTime(e.target.value)}
              className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">End time (optional)</label>
            <input
              type="datetime-local"
              value={endTime}
              onChange={e => setEndTime(e.target.value)}
              className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Notes</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Optional notes..."
              className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm"
              rows={2}
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={handleStartFast}>Save</Button>
            <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {/* Entries List */}
      <Card className="p-5">
        <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">All entries</h3>
        <div className="space-y-3">
          {entries.map(entry => (
            <div key={entry.id} className="flex items-center justify-between rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
              <div className="flex items-center gap-3">
                <div className="grid h-8 w-8 place-items-center rounded-lg bg-[oklch(0.72_0.15_178/0.15)]">
                  <Timer className="h-4 w-4 text-[oklch(0.48_0.12_255)]" />
                </div>
                <div>
                  <p className="font-bold text-sm">
                    {new Date(entry.start_time).toLocaleDateString()}
                  </p>
                  <p className="text-xs text-[oklch(0.48_0.035_255)]">
                    {entry.duration_minutes ? `${Math.round(entry.duration_minutes / 60)} hrs` : 'In progress'}
                  </p>
                </div>
              </div>
              <div className="text-right text-sm">
                {entry.end_time ? (
                  <p className="font-bold">{new Date(entry.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                ) : (
                  <span className="text-xs text-[oklch(0.48_0.035_255)]">Ongoing</span>
                )}
              </div>
            </div>
          ))}
          {entries.length === 0 && (
            <p className="text-sm text-[oklch(0.48_0.035_255)]">No fasting entries logged yet.</p>
          )}
        </div>
      </Card>
    </div>
  )
}