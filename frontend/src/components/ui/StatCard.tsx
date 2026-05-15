/** @jsxImportSource @emotion/react */
import { forwardRef } from 'react'
import type { ComponentProps } from 'react'
import { ArrowDownIcon, ArrowRightIcon, ArrowUpIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

const variantStyles = {
  default: 'from-[oklch(0.98_0.01_245)] to-[oklch(0.94_0.018_245)] text-[oklch(0.26_0.035_255)]',
  success: 'from-[oklch(0.96_0.035_178)] to-[oklch(0.9_0.055_178)] text-[oklch(0.32_0.09_174)]',
  warning: 'from-[oklch(0.97_0.04_75)] to-[oklch(0.92_0.07_75)] text-[oklch(0.45_0.1_63)]',
  danger: 'from-[oklch(0.97_0.032_26)] to-[oklch(0.92_0.06_26)] text-[oklch(0.44_0.12_27)]',
} as const

const trendStyles = {
  up: 'text-[oklch(0.56_0.18_27)]',
  down: 'text-[oklch(0.48_0.13_178)]',
  stable: 'text-[oklch(0.48_0.04_255)]',
} as const

type StatCardProps = ComponentProps<'div'> & {
  title?: string
  value?: string | number
  subtitle?: string
  trend?: 'up' | 'down' | 'stable'
  trendValue?: number
  icon?: React.ElementType
  variant?: keyof typeof variantStyles
}

export const StatCard = forwardRef(function StatCard(
  {
    className = '',
    title = '',
    value = '--',
    subtitle = '',
    trend = 'stable',
    trendValue = 0,
    icon: Icon,
    variant = 'default',
    ...props
  }: StatCardProps,
  ref: React.Ref<HTMLDivElement>
) {
  const TrendIcon = trend === 'up' ? ArrowUpIcon : trend === 'down' ? ArrowDownIcon : ArrowRightIcon

  return (
    <div
      ref={ref}
      className={cn(
        'relative overflow-hidden rounded-[26px] border border-[oklch(0.88_0.02_250)] bg-gradient-to-br p-5 shadow-signal',
        variantStyles[variant],
        className
      )}
      {...props}
    >
      <div className="absolute -right-8 -top-10 h-24 w-24 rounded-full bg-current opacity-[0.08]" />
      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.12em] opacity-70">{title}</p>
          <div className="mt-2 text-2xl font-black tracking-[-0.05em] md:text-[2rem]">{value}</div>
          {subtitle && <div className="mt-1 text-xs font-semibold opacity-65">{subtitle}</div>}
        </div>
        {Icon && (
          <div className="rounded-2xl border border-current/10 bg-[oklch(1_0_0/0.34)] p-2.5">
            <Icon className="h-5 w-5 opacity-75" />
          </div>
        )}
      </div>
      {trendValue > 0 && (
        <div className={cn('relative mt-4 inline-flex items-center gap-1 rounded-full bg-[oklch(1_0_0/0.38)] px-2.5 py-1 text-xs font-bold', trendStyles[trend])}>
          <TrendIcon className="h-3.5 w-3.5" />
          {trendValue.toFixed(0)} mg/dL since last reading
        </div>
      )}
    </div>
  )
})
