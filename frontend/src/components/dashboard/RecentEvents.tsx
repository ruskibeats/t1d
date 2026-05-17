import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { Bed, Dumbbell, FileText, Flame, Syringe, Utensils } from 'lucide-react'
import { ContextEvent } from '@/types'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

interface RecentEventsProps {
  events: ContextEvent[]
  loading: boolean
}

const eventMeta: Record<string, { icon: React.ElementType; tone: string; label: string }> = {
  meal: { icon: Utensils, tone: 'bg-[oklch(0.96_0.04_75)] text-[oklch(0.45_0.1_63)]', label: 'Meal' },
  insulin: { icon: Syringe, tone: 'bg-[oklch(0.95_0.035_292)] text-[oklch(0.46_0.13_292)]', label: 'Insulin' },
  exercise: { icon: Dumbbell, tone: 'bg-[oklch(0.95_0.04_178)] text-[oklch(0.34_0.1_174)]', label: 'Exercise' },
  sleep: { icon: Bed, tone: 'bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.12_255)]', label: 'Sleep' },
  stress: { icon: Flame, tone: 'bg-[oklch(0.96_0.035_27)] text-[oklch(0.48_0.13_27)]', label: 'Stress' },
}

export function RecentEvents({ events, loading }: RecentEventsProps) {
  const navigate = useNavigate()
  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-20 animate-pulse rounded-[22px] bg-[oklch(0.93_0.018_245)]" />
        ))}
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className="panel-subtle py-10 text-center">
        <FileText className="mx-auto mb-3 h-10 w-10 text-[oklch(0.62_0.06_255)]" />
        <p className="font-black tracking-[-0.02em]">No events yet</p>
        <p className="mx-auto mt-1 max-w-sm text-sm text-[oklch(0.48_0.035_255)]">Meals, movement, sleep, and stress make the glucose story easier to understand.</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={() => navigate('/events')}>Log first event</Button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {events.slice(0, 5).map((event) => {
        const meta = eventMeta[event.event_type] ?? { icon: FileText, tone: 'bg-[oklch(0.94_0.018_245)] text-[oklch(0.42_0.035_255)]', label: event.event_type }
        const Icon = meta.icon
        return (
          <div key={event.id} className="panel-subtle p-3.5 transition duration-200 hover:-translate-y-0.5 hover:shadow-signal">
            <div className="flex items-start gap-3">
              <div className={cn('grid h-11 w-11 shrink-0 place-items-center rounded-2xl', meta.tone)}>
                <Icon className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="font-black capitalize tracking-[-0.02em] text-[oklch(0.24_0.04_255)]">{meta.label}</h4>
                    {event.description && <p className="mt-0.5 truncate text-sm font-medium text-[oklch(0.48_0.035_255)]">{event.description}</p>}
                  </div>
                  <span className="shrink-0 rounded-full bg-[oklch(0.94_0.016_245)] px-2 py-1 text-[0.68rem] font-bold text-[oklch(0.48_0.035_255)]">
                    {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-[0.72rem] font-bold text-[oklch(0.48_0.035_255)]">
                  {event.carbs_grams && <span className="chip">{event.carbs_grams}g carbs</span>}
                  {event.insulin_units && <span className="chip">{event.insulin_units}u insulin</span>}
                  {event.duration && <span className="chip">{event.duration} min</span>}
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
