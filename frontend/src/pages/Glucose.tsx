/** @jsxImportSource @emotion/react */
import { useEffect } from 'react'
import { Activity, ArrowDownIcon, ArrowUpIcon, DatabaseZap, PlusIcon } from 'lucide-react'
import { format } from 'date-fns'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { GlucoseChart } from '@/components/charts/GlucoseChart'
import { useGlucose } from '@/hooks/useGlucose'
import { cn } from '@/lib/utils'

function statusFor(value: number) {
  if (value < 70) return { label: 'Low', className: 'bg-[oklch(0.96_0.035_27)] text-[oklch(0.48_0.13_27)]' }
  if (value > 180) return { label: 'High', className: 'bg-[oklch(0.96_0.04_75)] text-[oklch(0.45_0.1_63)]' }
  return { label: 'In range', className: 'bg-[oklch(0.95_0.04_178)] text-[oklch(0.34_0.1_174)]' }
}

export function GlucosePage() {
  const { readings, stats, loading, demoMode, fetchReadings } = useGlucose()

  useEffect(() => {
    fetchReadings('3d')
  }, [fetchReadings])

  const getTrendIcon = (current: number, previous: number | undefined) => {
    if (!previous) return <span className="text-[oklch(0.55_0.035_255)]">Stable</span>
    const diff = current - previous
    if (Math.abs(diff) < 5) return <span className="text-[oklch(0.55_0.035_255)]">Stable</span>
    return diff > 0
      ? <span className="inline-flex items-center gap-1 text-[oklch(0.56_0.18_27)]"><ArrowUpIcon className="h-4 w-4" /> +{diff.toFixed(0)}</span>
      : <span className="inline-flex items-center gap-1 text-[oklch(0.48_0.13_178)]"><ArrowDownIcon className="h-4 w-4" /> {diff.toFixed(0)}</span>
  }

  return (
    <div className="page-shell space-y-7">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="kicker"><span className="kicker-dot" /> Sensor trace</div>
          <h1 className="mt-2 text-4xl font-black tracking-[-0.06em] text-[oklch(0.22_0.04_255)]">Glucose readings</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[oklch(0.48_0.035_255)]">Review raw CGM and manual entries. {demoMode ? 'Demo data is shown until the backend has readings.' : 'Live data is connected.'}</p>
        </div>
        <Button><PlusIcon className="h-4 w-4" /> Add reading</Button>
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-[oklch(0.89_0.018_250)] p-5 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)]"><Activity className="h-5 w-5" /></div>
            <div>
              <h2 className="text-lg font-black tracking-[-0.03em]">Last 72 hours</h2>
              <p className="text-sm font-semibold text-[oklch(0.48_0.035_255)]">Average {stats.average.toFixed(0)} mg/dL, {stats.time_in_range.percentage.toFixed(0)}% in range</p>
            </div>
          </div>
          <span className="chip"><DatabaseZap className="h-3.5 w-3.5" /> {readings.length} readings</span>
        </div>
        <div className="p-4 md:p-5">
          <GlucoseChart readings={readings} timeRange="3d" />
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="border-b border-[oklch(0.89_0.018_250)] p-5">
          <h2 className="text-lg font-black tracking-[-0.03em]">Reading log</h2>
        </div>
        {loading ? (
          <div className="p-8 text-center font-semibold text-[oklch(0.48_0.035_255)]">Loading readings...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead>
                <tr className="bg-[oklch(0.96_0.012_245)] text-left text-[0.72rem] font-black uppercase tracking-[0.12em] text-[oklch(0.48_0.035_255)]">
                  <th className="px-5 py-3">Time</th>
                  <th className="px-5 py-3">Value</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Trend</th>
                  <th className="px-5 py-3">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[oklch(0.9_0.016_250)]">
                {readings.slice(0, 50).map((reading, index) => {
                  const previous = readings[index + 1]?.glucose_value
                  const status = statusFor(reading.glucose_value)
                  return (
                    <tr key={reading.id} className="transition hover:bg-[oklch(0.97_0.012_245)]">
                      <td className="px-5 py-4">
                        <div className="font-bold text-[oklch(0.24_0.04_255)]">{format(new Date(reading.timestamp), 'MMM d, h:mm a')}</div>
                        <div className="text-xs font-semibold text-[oklch(0.55_0.03_255)]">{format(new Date(reading.timestamp), 'yyyy-MM-dd')}</div>
                      </td>
                      <td className="px-5 py-4 text-xl font-black tracking-[-0.04em]">{reading.glucose_value} <span className="text-xs font-bold tracking-normal text-[oklch(0.5_0.035_255)]">mg/dL</span></td>
                      <td className="px-5 py-4"><span className={cn('rounded-full px-3 py-1 text-xs font-black', status.className)}>{status.label}</span></td>
                      <td className="px-5 py-4 text-sm font-bold">{getTrendIcon(reading.glucose_value, previous)}</td>
                      <td className="px-5 py-4"><span className="chip capitalize">{reading.source || 'manual'}</span></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

export default GlucosePage
