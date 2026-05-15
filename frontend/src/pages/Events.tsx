/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Activity, Bed, CalendarIcon, Dumbbell, Flame, PlusIcon, Syringe, Utensils } from 'lucide-react'
import { format } from 'date-fns'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useEvents } from '@/hooks/useEvents'
import { cn } from '@/lib/utils'

const filters = [
  { type: 'all', label: 'All events', icon: CalendarIcon },
  { type: 'meal', label: 'Meals', icon: Utensils },
  { type: 'insulin', label: 'Insulin', icon: Syringe },
  { type: 'exercise', label: 'Exercise', icon: Dumbbell },
  { type: 'sleep', label: 'Sleep', icon: Bed },
] as const

const icons: Record<string, React.ElementType> = {
  meal: Utensils,
  insulin: Syringe,
  exercise: Dumbbell,
  sleep: Bed,
  stress: Flame,
}

export function EventsPage() {
  const [selectedType, setSelectedType] = useState<'all' | 'meal' | 'insulin' | 'exercise' | 'sleep'>('all')
  const { events, demoMode } = useEvents()
  const filtered = selectedType === 'all' ? events : events.filter((event) => event.event_type === selectedType)

  return (
    <div className="page-shell space-y-7">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="kicker"><span className="kicker-dot" /> Context timeline</div>
          <h1 className="mt-2 text-4xl font-black tracking-[-0.06em] text-[oklch(0.22_0.04_255)]">Events</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[oklch(0.48_0.035_255)]">Food, insulin, exercise, sleep, and stress give the AI enough context to explain what usually happens. {demoMode ? 'Demo entries are visible.' : 'Live entries connected.'}</p>
        </div>
        <Button><PlusIcon className="h-4 w-4" /> New event</Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
        <Card className="p-5 lg:sticky lg:top-5 lg:self-start">
          <h2 className="text-lg font-black tracking-[-0.03em]">Filter</h2>
          <div className="mt-4 space-y-2">
            {filters.map((filter) => {
              const Icon = filter.icon
              return (
                <button
                  key={filter.type}
                  className={cn('flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font-black transition', selectedType === filter.type ? 'bg-[oklch(0.56_0.19_255)] text-[oklch(0.98_0.01_245)] shadow-[0_12px_26px_oklch(0.56_0.19_255/0.2)]' : 'text-[oklch(0.43_0.035_255)] hover:bg-[oklch(0.94_0.018_245)]')}
                  onClick={() => setSelectedType(filter.type)}
                >
                  <Icon className="h-4 w-4" /> {filter.label}
                </button>
              )
            })}
          </div>

          <div className="mt-6 rounded-[24px] bg-[oklch(0.95_0.025_255)] p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-black"><Activity className="h-4 w-4" /> Quick add</div>
            <p className="text-xs leading-5 text-[oklch(0.48_0.035_255)]">Prioritize moments that explain glucose movement: carbs, dosing, exercise, alcohol, stress, and illness.</p>
          </div>
        </Card>

        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-[oklch(0.89_0.018_250)] p-5">
            <div>
              <h2 className="text-lg font-black tracking-[-0.03em]">Timeline</h2>
              <p className="text-sm font-semibold text-[oklch(0.48_0.035_255)]">{filtered.length} entries in this view</p>
            </div>
            <Button variant="outline" size="sm">Week view</Button>
          </div>

          <div className="p-5">
            {filtered.length === 0 ? (
              <div className="panel-subtle py-14 text-center">
                <CalendarIcon className="mx-auto mb-3 h-12 w-12 text-[oklch(0.62_0.06_255)]" />
                <p className="font-black">No events in this filter</p>
                <p className="mt-1 text-sm text-[oklch(0.48_0.035_255)]">Try another filter or add your first event.</p>
              </div>
            ) : (
              <div className="relative space-y-3">
                {filtered.map((event) => {
                  const Icon = icons[event.event_type] ?? CalendarIcon
                  return (
                    <div key={event.id} className="panel-subtle grid gap-4 p-4 md:grid-cols-[auto_1fr_auto] md:items-center">
                      <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[oklch(0.94_0.03_245)] text-[oklch(0.42_0.12_255)]"><Icon className="h-5 w-5" /></div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-black capitalize tracking-[-0.02em]">{event.event_type}</h3>
                          <span className="chip">{format(new Date(event.timestamp), 'MMM d, h:mm a')}</span>
                        </div>
                        <p className="mt-1 text-sm font-semibold text-[oklch(0.48_0.035_255)]">{event.description ?? event.notes ?? 'Context event'}</p>
                      </div>
                      <div className="flex flex-wrap gap-2 md:justify-end">
                        {event.carbs_grams && <span className="chip">{event.carbs_grams}g carbs</span>}
                        {event.insulin_units && <span className="chip">{event.insulin_units}u</span>}
                        {event.duration && <span className="chip">{event.duration} min</span>}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

export default EventsPage
