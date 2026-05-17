/** @jsxImportSource @emotion/react */
import { useEffect, useState } from 'react'
import axios from 'axios'
import { Activity, Battery, HeartPulse, Plus, Wind } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { StatCard } from '@/components/ui/StatCard'

export function VitalsPage() {
  const [heart, setHeart] = useState<any[]>([])
  const [bp, setBp] = useState<any[]>([])
  const [vitals, setVitals] = useState<any[]>([])
  const [battery, setBattery] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ heart_rate_bpm: '', systolic: '', diastolic: '', spo2_percent: '', respiratory_rate: '', value: '' })

  const load = async () => {
    const [h, b, v, bb] = await Promise.allSettled([
      axios.get('/api/v1/heart'), axios.get('/api/v1/blood-pressure'), axios.get('/api/v1/vitals'), axios.get('/api/v1/body-battery'),
    ])
    if (h.status === 'fulfilled') setHeart(h.value.data ?? [])
    if (b.status === 'fulfilled') setBp(b.value.data ?? [])
    if (v.status === 'fulfilled') setVitals(v.value.data ?? [])
    if (bb.status === 'fulfilled') setBattery(bb.value.data ?? [])
  }

  useEffect(() => { load() }, [])

  const submit = async () => {
    const measured_at = new Date().toISOString()
    await Promise.allSettled([
      form.heart_rate_bpm ? axios.post('/api/v1/heart', { heart_rate_bpm: Number(form.heart_rate_bpm), measured_at, source: 'manual' }) : Promise.resolve(),
      form.systolic && form.diastolic ? axios.post('/api/v1/blood-pressure', { systolic: Number(form.systolic), diastolic: Number(form.diastolic), measured_at, source: 'manual' }) : Promise.resolve(),
      form.spo2_percent || form.respiratory_rate ? axios.post('/api/v1/vitals', { spo2_percent: form.spo2_percent ? Number(form.spo2_percent) : undefined, respiratory_rate: form.respiratory_rate ? Number(form.respiratory_rate) : undefined, measured_at, source: 'manual' }) : Promise.resolve(),
      form.value ? axios.post('/api/v1/body-battery', { value: Number(form.value), change: 0, measured_at, source: 'manual' }) : Promise.resolve(),
    ])
    setShowForm(false)
    setForm({ heart_rate_bpm: '', systolic: '', diastolic: '', spo2_percent: '', respiratory_rate: '', value: '' })
    await load()
  }

  const latestHeart = heart[0]
  const latestBp = bp[0]
  const latestVitals = vitals[0]
  const latestBattery = battery[0]

  return <div className="page-shell space-y-6">
    <div className="flex items-center justify-between">
      <div><div className="kicker"><span className="kicker-dot" /> Clinical context</div><h1 className="mt-2 text-4xl font-black tracking-[-0.06em]">Vitals</h1></div>
      <Button onClick={() => setShowForm(!showForm)}><Plus className="h-4 w-4" /> Log vitals</Button>
    </div>
    <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
      <StatCard title="Heart rate" value={latestHeart?.heart_rate_bpm ?? '--'} subtitle="bpm" icon={HeartPulse} variant="default" />
      <StatCard title="Blood pressure" value={latestBp ? `${latestBp.systolic}/${latestBp.diastolic}` : '--'} subtitle="mmHg" icon={Activity} variant="default" />
      <StatCard title="SpO2" value={latestVitals?.spo2_percent ?? '--'} subtitle="%" icon={Wind} variant="success" />
      <StatCard title="Body battery" value={latestBattery?.value ?? '--'} subtitle="/100" icon={Battery} variant="default" />
    </div>
    {showForm && <Card className="grid gap-3 p-5 md:grid-cols-3">
      <input className="control-input" placeholder="Heart rate bpm" value={form.heart_rate_bpm} onChange={e => setForm({ ...form, heart_rate_bpm: e.target.value })} />
      <input className="control-input" placeholder="Systolic" value={form.systolic} onChange={e => setForm({ ...form, systolic: e.target.value })} />
      <input className="control-input" placeholder="Diastolic" value={form.diastolic} onChange={e => setForm({ ...form, diastolic: e.target.value })} />
      <input className="control-input" placeholder="SpO2 %" value={form.spo2_percent} onChange={e => setForm({ ...form, spo2_percent: e.target.value })} />
      <input className="control-input" placeholder="Respiratory rate" value={form.respiratory_rate} onChange={e => setForm({ ...form, respiratory_rate: e.target.value })} />
      <input className="control-input" placeholder="Body battery" value={form.value} onChange={e => setForm({ ...form, value: e.target.value })} />
      <Button onClick={submit}>Save vitals</Button>
    </Card>}
    <Card className="p-5"><h2 className="mb-4 text-lg font-black">Recent vitals</h2><div className="space-y-2 text-sm font-semibold text-[oklch(0.48_0.035_255)]">
      {[...heart, ...bp, ...vitals, ...battery].slice(0, 12).map((entry, index) => <div key={index} className="rounded-xl bg-[oklch(0.96_0.02_245)] p-3">{new Date(entry.measured_at).toLocaleString()} · {entry.source ?? 'manual'}</div>)}
    </div></Card>
  </div>
}

export default VitalsPage
