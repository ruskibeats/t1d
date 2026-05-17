/** @jsxImportSource @emotion/react */
import { useEffect, useState } from 'react'
import { Plus, Ruler, Activity, Percent, Bone } from 'lucide-react'
import axios from 'axios'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useMeasurements } from '@/hooks/useMeasurements'

const metricTypes = [
  { value: 'weight', label: 'Weight', unit: 'kg', icon: Activity },
  { value: 'body_fat', label: 'Body Fat', unit: '%', icon: Percent },
  { value: 'muscle_mass', label: 'Muscle Mass', unit: 'kg', icon: Activity },
  { value: 'bone_density', label: 'Bone Density', unit: 'g/cm²', icon: Bone },
  { value: 'bmi', label: 'BMI', unit: '', icon: Ruler },
]

export function MeasurementsLogPage() {
  const { entries, createEntry } = useMeasurements()
  const [bodyCompData, setBodyCompData] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [metricName, setMetricName] = useState('weight')
  const [value, setValue] = useState('')
  const [unit, setUnit] = useState('kg')
  const [note, setNote] = useState('')

  useEffect(() => {
    axios.get('/api/v1/body-composition').then(r => setBodyCompData(r.data ?? [])).catch(() => undefined)
  }, [])

  const handleAdd = async () => {
    if (!value) return
    await createEntry({
      metric_name: metricName,
      value: parseFloat(value),
      unit,
      note,
    })
    setShowForm(false)
    setValue('')
    setNote('')
  }

  // Calculate stats
  const weightEntries = entries.filter(e => e.metric_name === 'weight')
  const current = weightEntries[0]?.value || 0
  const avg = weightEntries.reduce((sum, e) => sum + e.value, 0) / (weightEntries.length || 1)

  return (
    <div className="page-shell space-y-6">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Body metrics</div>
        <h2 className="mt-2 text-2xl font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">Measurements</h2>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="p-4 text-center">
          <Activity className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{current || '--'}</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Current (kg)</p>
        </Card>
        <Card className="p-4 text-center">
          <Activity className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{avg.toFixed(1)}</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Average</p>
        </Card>
        <Card className="p-4 text-center">
          <Percent className="mx-auto mb-2 h-5 w-5 text-[oklch(0.56_0.19_255)]" />
          <p className="text-2xl font-black">{weightEntries.length}</p>
          <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Entries</p>
        </Card>
      </div>

      {/* Add Measurement Button */}
      <Button onClick={() => setShowForm(true)} className="w-full">
        <Plus className="h-4 w-4" /> Add measurement
      </Button>

      {/* Form Modal */}
      {showForm && (
        <Card className="p-5 space-y-4">
          <h3 className="font-black">New measurement</h3>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Metric</label>
            <select
              value={metricName}
              onChange={e => {
                setMetricName(e.target.value)
                const mt = metricTypes.find(m => m.value === e.target.value)
                if (mt) setUnit(mt.unit)
              }}
              className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm"
            >
              {metricTypes.map(mt => (
                <option key={mt.value} value={mt.value}>{mt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Value</label>
            <input
              type="number"
              value={value}
              onChange={e => setValue(e.target.value)}
              placeholder="Enter value"
              step="0.1"
              className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Unit</label>
            <input
              type="text"
              value={unit}
              onChange={e => setUnit(e.target.value)}
              className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Note</label>
            <textarea
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="Optional note..."
              className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm"
              rows={2}
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={handleAdd}>Save</Button>
            <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {/* Body Composition Section */}
      {bodyCompData.length > 0 && (
        <Card className="p-5">
          <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">Body composition</h3>
          <div className="grid grid-cols-5 gap-3">
            {['weight_kg','body_fat_percent','bmi','lean_mass_kg','waist_cm'].map(field => {
              const latest = bodyCompData[0]
              const label = field.replace('_',' ')
              const suffix = field.includes('percent') ? '%' : field === 'bmi' ? '' : field.endsWith('kg') ? 'kg' : 'cm'
              return <div key={field} className="rounded-xl bg-[oklch(0.96_0.02_245)] p-3 text-center">
                <p className="text-xl font-black">{latest[field] ?? '--'}</p>
                <p className="text-xs font-bold capitalize">{label} {suffix}</p>
              </div>
            })}
          </div>
        </Card>
      )}

      {/* Entries List */}
      <Card className="p-5">
        <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">All measurements</h3>
        <div className="space-y-3">
          {entries.map(entry => (
            <div key={entry.id} className="flex items-center justify-between rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
              <div className="flex items-center gap-3">
                <div className="grid h-8 w-8 place-items-center rounded-lg bg-[oklch(0.72_0.15_178/0.15)]">
                  <Ruler className="h-4 w-4 text-[oklch(0.48_0.12_255)]" />
                </div>
                <div>
                  <p className="font-bold text-sm">{entry.metric_name.replace('_', ' ')}</p>
                  <p className="text-xs text-[oklch(0.48_0.035_255)]">{entry.value} {entry.unit}</p>
                </div>
              </div>
              <div className="text-right text-sm">
                <p className="text-xs text-[oklch(0.48_0.035_255)]">
                  {new Date(entry.measured_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
          {entries.length === 0 && (
            <p className="text-sm text-[oklch(0.48_0.035_255)]">No measurements logged yet.</p>
          )}
        </div>
      </Card>
    </div>
  )
}