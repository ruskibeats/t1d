/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Award, Brain, CheckCircle2, Flame, Sparkles, Target, TrendingUp } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { cn } from '@/lib/utils'

interface Streak {
  label: string
  days: number
  icon: typeof Flame
  color: string
}

interface Achievement {
  title: string
  description: string
  earned: boolean
  icon: typeof Award
}

export function CoachPage() {
  const [streaks] = useState<Streak[]>([
    { label: 'Steady mornings', days: 10, icon: Flame, color: 'text-[oklch(0.52_0.12_73)]' },
    { label: 'Logging meals', days: 7, icon: Target, color: 'text-[oklch(0.43_0.13_178)]' },
    { label: 'In range overnight', days: 5, icon: CheckCircle2, color: 'text-[oklch(0.43_0.13_178)]' },
  ])

  const [achievements] = useState<Achievement[]>([
    { title: 'First week logged', description: 'You logged data for 7 days in a row.', earned: true, icon: Award },
    { title: 'Pattern spotter', description: 'You reviewed your patterns 3 times this week.', earned: true, icon: Brain },
    { title: 'Evening wins', description: 'Evening highs improved this week compared to last.', earned: false, icon: TrendingUp },
    { title: '30-day streak', description: 'Log data for 30 days in a row.', earned: false, icon: Sparkles },
  ])

  return (
    <div className="page-shell space-y-6">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Progress</div>
        <h1 className="mt-2 text-3xl font-black tracking-[-0.06em] text-[oklch(0.22_0.04_255)]">Coach</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[oklch(0.48_0.035_255)]">
          Gentle progress tracking. No childish rewards — just honest observations about your patterns.
        </p>
      </div>

      {/* Streaks */}
      <div>
        <h2 className="mb-3 text-lg font-black tracking-[-0.03em]">Current streaks</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {streaks.map((streak) => {
            const Icon = streak.icon
            return (
              <Card key={streak.label} className="p-5">
                <div className="flex items-center gap-3">
                  <div className={cn('grid h-12 w-12 place-items-center rounded-2xl bg-[oklch(0.96_0.02_245)]')}>
                    <Icon className={cn('h-6 w-6', streak.color)} />
                  </div>
                  <div>
                    <p className="text-2xl font-black">{streak.days}</p>
                    <p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">{streak.label}</p>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Achievements */}
      <div>
        <h2 className="mb-3 text-lg font-black tracking-[-0.03em]">Achievements</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {achievements.map((achievement) => {
            const Icon = achievement.icon
            return (
              <Card key={achievement.title} className={cn(
                'p-5 flex items-start gap-4',
                achievement.earned ? 'border border-[oklch(0.72_0.15_178/0.2)] bg-[oklch(0.72_0.15_178/0.04)]' : 'opacity-60'
              )}>
                <div className={cn(
                  'grid h-10 w-10 shrink-0 place-items-center rounded-2xl',
                  achievement.earned ? 'bg-[oklch(0.72_0.15_178/0.12)]' : 'bg-[oklch(0.94_0.035_255)]'
                )}>
                  <Icon className={cn('h-5 w-5', achievement.earned ? 'text-[oklch(0.43_0.13_178)]' : 'text-[oklch(0.48_0.035_255)]')} />
                </div>
                <div>
                  <p className="font-black">{achievement.title}</p>
                  <p className="mt-1 text-sm text-[oklch(0.48_0.035_255)]">{achievement.description}</p>
                  {achievement.earned && (
                    <span className="mt-2 inline-block rounded-full bg-[oklch(0.72_0.15_178/0.12)] px-2 py-0.5 text-[0.65rem] font-black text-[oklch(0.43_0.13_178)]">Earned</span>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Weekly insight */}
      <Card className="p-5">
        <div className="flex items-start gap-3">
          <Brain className="h-5 w-5 shrink-0 text-[oklch(0.46_0.15_255)]" />
          <div>
            <h3 className="font-black">This week's insight</h3>
            <p className="mt-2 text-sm leading-6 text-[oklch(0.36_0.035_255)]">
              Your morning glucose has been more stable this week. The evenings are still a bit variable —
              that is normal and worth watching. You are building a good picture of your patterns.
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default CoachPage
