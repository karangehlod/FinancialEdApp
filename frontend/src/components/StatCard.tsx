import { Card, FluidIcon } from './UI'
import { memo } from 'react'
import { cn } from '@/utils/helpers'
import type { IconComponent } from './UI'

interface StatCardProps {
  readonly title: string
  readonly value: string | number
  readonly icon?: IconComponent
  readonly trend?: { value: number; positive: boolean }
  readonly className?: string
}

export const StatCard = memo<StatCardProps>(function StatCard({ title, value, icon: Icon, trend, className }) {
  return (
    <div className={cn('min-w-0')}> {/* ensures no overflow when inside grid */}
      <Card className={cn('h-full flex flex-col justify-between', className)}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm-fluid font-medium text-gray-500 dark:text-gray-400 truncate">{title}</p>
            <p className="text-value text-gray-900 dark:text-gray-100 mt-1">{value}</p>
            {trend && (
              <p className={cn('text-sm-fluid mt-1 font-medium', trend.positive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400')}>
                {trend.positive ? '↑' : '↓'} {Math.abs(trend.value)}%
              </p>
            )}
          </div>
          {Icon && (
            <div className="flex-shrink-0 ml-2" style={{ width: 'var(--icon-md)', height: 'var(--icon-md)' }}>
              <FluidIcon icon={Icon} size="md" className="text-primary-500" />
            </div>
          )}
        </div>
      </Card>
    </div>
  )
})
