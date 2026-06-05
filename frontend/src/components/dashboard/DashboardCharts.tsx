import React from 'react'
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  Tooltip as RechartTooltip,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts'
import { useCurrency } from '../../hooks/useCurrency'

const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#6366F1']

export const ExpenseDistributionChart: React.FC<{ data: Array<{ name: string; value: number }> }> = ({ data }) => {
  const { formatCurrency } = useCurrency()

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-80 text-gray-400">
        <p>No expense data available</p>
      </div>
    )
  }

  const tooltipFormatter = (value: number | string) => formatCurrency(Number(value))

  return (
    <div className="space-y-4 h-full flex flex-col">
      <div className="flex-1 min-h-0" style={{ height: 'calc(100% - var(--chart-info-height))' }}>
        {/* Use full-height ResponsiveContainer so the pie fills its allocated visual area */}
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={48}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(1)}%`}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <RechartTooltip formatter={tooltipFormatter as any} />
            <Legend
              verticalAlign="bottom"
              height={48}
              formatter={(_value: any, entry: any) => `${entry?.payload?.name ?? ''}: ${formatCurrency(entry?.payload?.value ?? 0)}`}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3" style={{ height: 'var(--chart-info-height)', overflow: 'auto' }}>
        <div className="grid grid-cols-2 gap-3">
          {data.map((item, index) => (
            <div key={index} className="p-2 bg-gray-50 dark:bg-gray-700 rounded-lg flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
              <div className="flex-1">
                <p className="text-xs text-gray-600 dark:text-gray-400">{item.name}</p>
                <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{formatCurrency(item.value)}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export const SpendingTrendChart: React.FC<{ data: Array<{ date: string; amount: number }>; viewType?: string }> = ({ data, viewType = '30days' }) => {
  const { formatCurrency } = useCurrency()

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-80 text-gray-400">
        <p>No spending data available</p>
      </div>
    )
  }

  const tooltipFormatter = (value: number | string) => formatCurrency(Number(value))

  // Adjust X axis layout to avoid taking too much vertical space when there are many ticks
  const points = data.length
  const isDense = points > 12
  const xAxisAngle = viewType === '30days' ? (isDense ? -30 : -45) : 0
  const xAxisHeight = viewType === '30days' ? (isDense ? 50 : 70) : 30
  const chartMargin = { top: 5, right: 30, left: 0, bottom: 10 }

  return (
    <div className="h-full flex-1 min-h-0">
      {/* Use full-height ResponsiveContainer so the line chart fills its parent (avoids small chart when parent is tall) */}
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={chartMargin}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey={viewType === '30days' ? 'date' : viewType === 'yearly' ? 'year' : 'month'}
            stroke="#6b7280"
            angle={xAxisAngle}
            textAnchor={xAxisAngle ? 'end' : 'middle'}
            height={xAxisHeight}
            interval={isDense ? Math.ceil(points / 12) : 0}
          />
          <YAxis stroke="#6b7280" />
          <RechartTooltip
            formatter={tooltipFormatter as any}
            labelFormatter={(label: React.ReactNode) => {
              const labelText = String(label ?? '')
              if (viewType === '30days') return `Date: ${labelText}`
              if (viewType === 'yearly') return `Year: ${labelText}`
              return `Month: ${labelText}`
            }}
          />
          <Line type="monotone" dataKey="amount" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6', r: viewType === '30days' ? 3 : 5 }} activeDot={{ r: 6 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export const BudgetUtilizationChart: React.FC<{ data: Array<{ name: string; allocated: number; spent: number }> }> = ({ data }) => {
  const { formatCurrency } = useCurrency()

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-80 text-gray-400">
        <p>No budget data available</p>
      </div>
    )
  }

  const tooltipFormatter = (value: number | string) => formatCurrency(Number(value))

  return (
    <ResponsiveContainer width="100%" height={100}>
      <BarChart data={data} margin={{ top: 0, right: 30, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="name" stroke="#6b7280" angle={-45} textAnchor="end" height={60} />
        <YAxis stroke="#6b7280" />
        <RechartTooltip formatter={tooltipFormatter as any} labelFormatter={(label) => `Category: ${label}`} />
        <Legend formatter={(value) => (value === 'allocated' ? 'Budget Allocated' : 'Amount Spent')} wrapperStyle={{ paddingTop: '12px' }} />
        <Bar dataKey="allocated" fill="#10B981" name="allocated" />
        <Bar dataKey="spent" fill="#ef4444" name="spent" />
      </BarChart>
    </ResponsiveContainer>
  )
}
