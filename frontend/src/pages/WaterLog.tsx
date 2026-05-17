/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Droplet, Plus, Target } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useWater } from '@/hooks/useWater'

const DAILY_GOAL_ML = 2000

export function WaterLogPage() {
  const { entries, createEntry, getTodayTotal } = useWater()
  const [showForm, setShowForm] = useState(false)
  const [amount, setAmount] = useState(250)

  const handleAdd = async () => {
    await createEntry({ amount_ml: amount })
    setShowForm(false)
  }

  const todayTotal = getTodayTotal()
  const progress = Math.min(100, (todayTotal / DAILY_GOAL_ML) * 100)

  return (
    <div className="page-shell space-y-6">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Hydration tracking</div>
        <h2 className="mt-2 text-2xl font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">Water log</h2>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 gap-3">
        <Card className="p-4 text-center">
          <Droplet className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{Math.round(todayTotal / 1000)}</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Liters today</p>
        </Card>
        <Card className="p-4 text-center">
          <Target className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{Math.round(progress)}%</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Daily goal</p>
        </Card>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-[oklch(0.92_0.01_250)] rounded-full h-4">
        <div 
          className="bg-[oklch(0.56_0.19_255)] h-4 rounded-full transition-all duration-300" 
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Add Water Button */}
      <Button onClick={() => setShowForm(true)} className="w-full">
        <Plus className="h-4 w-4" /> Log water
      </Button>

      {/* Form Modal */}
      {showForm && (
        <Card className="p-5 space-y-4">
          <h3 className="font-black">Log water intake</h3>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)] mb-2 block">Amount (ml)</label>
            <div className="flex gap-2">
              {[250, 500, 750, 1000].map(preset => (
                <Button 
                  key={preset} 
                  size="sm" 
                  variant={amount === preset ? 'primary' : 'ghost'}
                  onClick={() => setAmount(preset)}
                >
                  {preset}ml
                </Button>
              ))}
            </div>
            <input
              type="number"
              value={amount}
              onChange={e => setAmount(parseInt(e.target.value) || 0)}
              min="50"
              max="5000"
              step="50"
              className="mt-2 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm"
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={handleAdd}>Save</Button>
            <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {/* Entries List */}
      <Card className="p-5">
        <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">Recent entries</h3>
        <div className="space-y-3">
          {entries.map(entry => (
            <div key={entry.id} className="flex items-center justify-between rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
              <div className="flex items-center gap-3">
                <div className="grid h-8 w-8 place-items-center rounded-lg bg-[oklch(0.72_0.15_178/0.15)]">
                  <Droplet className="h-4 w-4 text-[oklch(0.48_0.12_255)]" />
                </div>
                <div>
                  <p className="font-bold text-sm">{entry.amount_ml} ml</p>
                  <p className="text-xs text-[oklch(0.48_0.035_255)]">{new Date(entry.logged_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                </div>
              </div>
            </div>
          ))}
          {entries.length === 0 && (
            <p className="text-sm text-[oklch(0.48_0.035_255)]">No water entries logged yet.</p>
          )}
        </div>
      </Card>
    </div>
  )
}