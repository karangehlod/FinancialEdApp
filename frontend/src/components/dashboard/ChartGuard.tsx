import React, { ReactNode, useEffect } from 'react'
import { useMeasuredRect } from '../../hooks/useMeasuredRect'
import { LoadingSpinner } from '../UI'

interface ChartGuardProps {
  children: ReactNode
  className?: string
  sync?: (height: number) => void
}

export const ChartGuard: React.FC<ChartGuardProps> = ({ children, className = '', sync }) => {
  const { ref, rect } = useMeasuredRect<HTMLDivElement>()

  useEffect(() => {
    if (sync && rect.height > 0) sync(rect.height)
  }, [rect.height])

  return (
    <div ref={ref as any} className={className}>
      {rect.width > 0 && rect.height > 0 ? (
        children
      ) : (
        <div className="flex items-center justify-center p-6">
          <LoadingSpinner size="lg" />
        </div>
      )}
    </div>
  )
}
