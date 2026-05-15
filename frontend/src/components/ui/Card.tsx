/** @jsxImportSource @emotion/react */
import { forwardRef } from 'react'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

export const Card = forwardRef(function Card(
  { className = '', children, ...props }: ComponentProps<'div'>,
  ref: React.Ref<HTMLDivElement>
) {
  return (
    <div
      ref={ref}
      className={cn('panel shadow-signal', className)}
      {...props}
    >
      {children}
    </div>
  )
})
