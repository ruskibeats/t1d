/** @jsxImportSource @emotion/react */
import { forwardRef } from 'react'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

const buttonVariants = {
  primary: 'bg-[oklch(0.56_0.19_255)] text-[oklch(0.98_0.01_245)] shadow-[0_12px_30px_oklch(0.56_0.19_255/0.24)] hover:bg-[oklch(0.51_0.19_255)]',
  secondary: 'bg-[oklch(0.94_0.018_245)] text-[oklch(0.28_0.035_255)] hover:bg-[oklch(0.91_0.02_245)]',
  ghost: 'text-[oklch(0.34_0.035_255)] hover:bg-[oklch(0.93_0.018_245)]',
  destructive: 'bg-[oklch(0.62_0.18_27)] text-[oklch(0.98_0.01_245)] hover:bg-[oklch(0.56_0.18_27)]',
  outline: 'border border-[oklch(0.86_0.022_250)] bg-[oklch(0.99_0.008_245/0.72)] text-[oklch(0.33_0.035_255)] hover:bg-[oklch(0.95_0.014_245)]',
} as const

type ButtonVariant = keyof typeof buttonVariants
type ButtonSize = 'sm' | 'md' | 'lg'

type ButtonProps = ComponentProps<'button'> & {
  variant?: ButtonVariant
  size?: ButtonSize
}

export const Button = forwardRef(function Button(
  {
    className = '',
    variant = 'primary',
    size = 'md',
    children,
    disabled = false,
    ...props
  }: ButtonProps,
  ref: React.ForwardedRef<HTMLButtonElement>
) {
  const sizeClasses: Record<ButtonSize, string> = {
    sm: 'h-8 px-3 text-xs',
    md: 'h-10 px-4 text-sm',
    lg: 'h-12 px-5 text-base',
  }

  return (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-2xl font-semibold tracking-[-0.01em]',
        'transition-[background,box-shadow,transform,border-color,color] duration-200 ease-out',
        'hover:-translate-y-0.5 active:translate-y-0',
        'focus:outline-none focus:ring-4 focus:ring-[oklch(0.56_0.19_255/0.18)]',
        'disabled:cursor-not-allowed disabled:opacity-45 disabled:translate-y-0 disabled:shadow-none',
        buttonVariants[variant],
        sizeClasses[size],
        className
      )}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
})
