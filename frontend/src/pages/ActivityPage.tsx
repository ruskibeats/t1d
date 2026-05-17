/** @jsxImportSource @emotion/react */
import { useEffect, useState } from 'react'
import axios from 'axios'
import { Footprints, Mountain, Plus, Route } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { StatCard } from '@/components/ui/StatCard'

export function ActivityPage() {
  const [entries, setEntries] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ steps: '', distance_km: '', floors_climbed: '' })

  const load = async () => {
    const res = await axios.get('/api/v1/activity')
    setEntries(res.data ?? [])
  }
  useEffect(() => { load().catch(() => undefined) }, [])

  const submit = async () => {
    await axios.post('/api/v1/activity', {
      steps: form.steps ? Number(form.steps) : undefined,
      distance_km: form.distance_km ? Number(form.distance_km) : undefined,
      floors_climbed: form.floors_climbed ? Number(form.floors_climbed) : undefined,
      measured_at: new Date().toISOString(),
      source: 'manual',
    })
    setShowForm(false)
    setForm({ steps: '', distance_km: '', floors_climbed: '' })
    await load()
  }

  const totalSteps = entries.reduce((s, e) => s + (e.steps ?? 0), 0)
  const totalDistance = entries.reduce((s, e) => s + (e.distance_km ?? 0), 0)
  const totalFloors = entries.reduce((s, e) => s + (e.floors_climbed ?? 0), 0)

  return <div className="page-shell space-y-6">
    <div className="flex items-center justify-between">
      <div><div className="kicker"><span className="kicker-dot" /> Physical Activity</div><h1 className="mt-2 text-4xl font-black tracking-[-0.06em]">Activity</h1></div>
      <Button onClick={() => setShowForm(!showForm)}><Plus className="h-4 w-4" /> Log activity</Button>
    </div>
    <div className="grid grid-cols-3 gap-4">
      <StatCard title="Total steps" value={totalSteps.toLocaleString()} subtitle="steps" icon={Footprints} variant="success" />
      <StatCard title="Distance" value={totalDistance.toFixed(1)} subtitle="km" icon={Route} variant="default" />
      <StatCard title="Floors" value={totalFloors.toString()} subtitle="floors" icon={Mountain} variant="default" />
    </div>
    {showForm && <Card className="grid gap-3 p-5 md:grid-cols-3">
      <div><label className="text-xs font-bold">Steps</label><input className="control-input" type="number" value={form.steps} onChange={e => setForm({...form, steps: e.target.value})} /></div>
      <div><label className="text-xs font-bold">Distance (km)</label><input className="control-input" type="number" value={form.distance_km} onChange={e => setForm({...form, distance_km: e.target.value})} /></div>
      <div><label className="text-xs font-bold">Floors climbed</label><input className="control-input" type="number" value={form.floors_climbed} onChange={e => setForm({...form, floors_climbed: e.target.value})} /></div>
      <Button onClick={submit}>Save</Button>
    </Card>}
    <Card className="p-5"><h2 className="mb-4 text-lg font-black">Recent entries</h2><div className="space-y-2 text-sm font-semibold text-[oklch(0.48_0.035_255)]">
      {entries.length === 0 && <p>No activity entries yet.</p>}
      {entries.slice(0, 20).map(e => <div key={e.id} className="rounded-xl bg-[oklch(0.96_0.02_245)] p-3 flex justify-between">
        <span>{new Date(e.measured_at).toLocaleDateString()}</span>
        <span>{e.steps ? `${e.steps.toLocaleString()} steps` : ''}{e.distance_km ? ` · ${e.distance_km}km` : ''}{e.floors_climbed ? ` · ${e.floors_climbed} floors` : ''}</span>
      </div>)}
    </div></Card>
  </div>
}

export default ActivityPage
