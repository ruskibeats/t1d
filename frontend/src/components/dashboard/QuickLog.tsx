/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Activity, Dumbbell, PlusIcon, Syringe, Utensils, XIcon } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

const quickActions = [
  { label: 'Glucose', icon: Activity, detail: 'Manual reading', tone: 'bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)]' },
  { label: 'Meal', icon: Utensils, detail: 'Carbs and notes', tone: 'bg-[oklch(0.96_0.04_75)] text-[oklch(0.45_0.1_63)]' },
  { label: 'Insulin', icon: Syringe, detail: 'Dose record', tone: 'bg-[oklch(0.95_0.035_292)] text-[oklch(0.46_0.13_292)]' },
  { label: 'Exercise', icon: Dumbbell, detail: 'Duration and intensity', tone: 'bg-[oklch(0.95_0.04_178)] text-[oklch(0.34_0.1_174)]' },
]

export function QuickLog() {
  const [expanded, setExpanded] = useState(true)

  if (!expanded) {
    return (
      <button className="panel-subtle flex w-full items-center justify-center gap-2 p-5 text-sm font-black text-[oklch(0.44_0.035_255)] transition hover:-translate-y-0.5 hover:shadow-signal" onClick={() => setExpanded(true)}>
        <PlusIcon className="h-4 w-4" /> Quick log
      </button>
    )
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-bold text-[oklch(0.48_0.035_255)]">Capture context fast</p>
        <Button variant="ghost" size="sm" onClick={() => setExpanded(false)} aria-label="Collapse quick log">
          <XIcon className="h-4 w-4" />
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-1">
        {quickActions.map((action) => {
          const Icon = action.icon
          return (
            <button
              key={action.label}
              className="panel-subtle flex items-center gap-3 p-3 text-left transition duration-200 hover:-translate-y-0.5 hover:shadow-signal"
              onClick={() => console.info(`Quick log ${action.label}`)}
            >
              <div className={cn('grid h-10 w-10 place-items-center rounded-2xl', action.tone)}>
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <div className="font-black tracking-[-0.02em] text-[oklch(0.24_0.04_255)]">{action.label}</div>
                <div className="text-xs font-semibold text-[oklch(0.5_0.035_255)]">{action.detail}</div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
