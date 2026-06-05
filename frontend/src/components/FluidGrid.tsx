import type { ReactNode, HTMLAttributes } from 'react'
import { memo } from 'react'
import { cn } from '@/utils/helpers'

interface FluidGridProps extends HTMLAttributes<HTMLDivElement> {
  readonly children: ReactNode
  /** Minimum column width for grid items (overrides default token) */
  readonly min?: string
}

/**
 * FluidGrid — grid wrapper using auto-fit + minmax for continuous wrapping.
 * Accepts `min` prop to override the min size (e.g., '240px').
 */
export const FluidGrid = memo<FluidGridProps>(function FluidGrid({ children, className, min, ...rest }) {
  const style = min ? { gridTemplateColumns: `repeat(auto-fit, minmax(${min}, 1fr))` } as any : undefined
  return (
    <div className={cn('fluid-grid', className)} style={style} {...rest}>
      {children}
    </div>
  )
})
