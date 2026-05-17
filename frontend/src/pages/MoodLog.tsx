/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Smile, Frown, Plus, Activity } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useMood } from '@/hooks/useMood'

const moodEmojis = ['😞', '😟', '😕', '😐', '🙂', '😊', '😄', '😁', '🤗', '🥰', '😍']

export function MoodLogPage() {
  const { entries, createEntry, getWeekAverage } = useMood()
  const [showForm, setShowForm] = useState(false)
  const [score, setScore] = useState(5)
  const [notes, setNotes] = useState('')

  const handleLog = async () => {
    await createEntry({ score, notes })
    setShowForm(false)
    setScore(5)
    setNotes('')
  }

  const weekAvg = getWeekAverage()

  return (
    <div className="page-shell space-y-6">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Mental wellness</div>
        <h2 className="mt-2 text-2xl font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">Mood log</h2>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="p-4 text-center">
          <Smile className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{weekAvg.toFixed(1)}</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">7-day avg</p>
        </Card>
        <Card className="p-4 text-center">
          <Frown className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{entries[0]?.score || '--'}</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Today</p>
        </Card>
        <Card className="p-4 text-center">
          <Activity className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{entries.length}</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Total</p>
        </Card>
      </div>

      {/* Add Mood Button */}
      <Button onClick={() => setShowForm(true)} className="w-full">
        <Plus className="h-4 w-4" /> Log mood
      </Button>

      {/* Form Modal */}
      {showForm && (
        <Card className="p-5 space-y-4">
          <h3 className="font-black">How are you feeling?</h3>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)] mb-2 block">Mood (1-10)</label>
            <div className="flex items-center gap-3">
              <Frown className="h-5 w-5 text-[oklch(0.48_0.035_255)]" />
              <input
                type="range"
                min="1"
                max="10"
                value={score}
                onChange={e => setScore(parseInt(e.target.value))}
                className="flex-1"
              />
              <Smile className="h-5 w-5 text-[oklch(0.56_0.19_255)]" />
              <span className="text-2xl">{moodEmojis[score - 1] || '😐'}</span>
            </div>
            <p className="text-center text-sm font-bold mt-1">{score}/10</p>
          </div>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="How are you feeling today?"
              className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm"
              rows={2}
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={handleLog}>Save</Button>
            <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {/* Entries List */}
      <Card className="p-5">
        <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">Mood history</h3>
        <div className="space-y-3">
          {entries.map(entry => (
            <div key={entry.id} className="flex items-center justify-between rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
              <div className="flex items-center gap-3">
                <div className="grid h-8 w-8 place-items-center rounded-lg bg-[oklch(0.72_0.15_178/0.15)]">
                  <span className="text-lg">{moodEmojis[entry.score - 1] || '😐'}</span>
                </div>
                <div>
                  <p className="font-bold text-sm">{entry.score}/10 {entry.notes && `· ${entry.notes}`}</p>
                  <p className="text-xs text-[oklch(0.48_0.035_255)]">{new Date(entry.logged_at).toLocaleDateString()}</p>
                </div>
              </div>
            </div>
          ))}
          {entries.length === 0 && (
            <p className="text-sm text-[oklch(0.48_0.035_255)]">No mood entries logged yet.</p>
          )}
        </div>
      </Card>
    </div>
  )
}