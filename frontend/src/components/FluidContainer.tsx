import type { ReactNode, HTMLAttributes } from 'react'
import { memo } from 'react'
import { cn } from '@/utils/helpers'

interface FluidContainerProps extends HTMLAttributes<HTMLDivElement> {
  readonly children: ReactNode
}

/**
 * FluidContainer — lightweight presentational wrapper that applies
 * the centralized fluid layout token (.fluid-container).
 *
 * Use this to replace rigid max-width wrappers so pages scale continuously.
 */
export const FluidContainer = memo<FluidContainerProps>(function FluidContainer({ children, className, ...rest }) {
  return (
    <div className={cn('fluid-container', className)} {...rest}>
      {children}
    </div>
  )
})
