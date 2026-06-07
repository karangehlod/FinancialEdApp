import React from 'react'
import { ResponsiveContainer, PieChart, Pie, Cell, Legend, Tooltip, LineChart, Line, XAxis, YAxis, CartesianGrid, BarChart, Bar } from 'recharts'
import { formatCurrency } from '../../utils/helpers'
import { useCurrency } from '../../hooks/useCurrency'

const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']

// Component: Expense Distribution Pie Chart
export const ExpenseDistributionChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-80 text-gray-400">
        <p>No expense data available</p>
      </div>
    )
  }

  const { formatCurrency: formatWithGlobal } = useCurrency()

  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, value, percent }) => `${name}: ${formatWithGlobal(value)} (${(percent * 100).toFixed(1)}%)`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => formatWithGlobal(value)} />
          <Legend 
            verticalAlign="bottom" 
            height={36}
            formatter={(value, entry) => `${entry.payload.name}: ${formatWithGlobal(entry.payload.value)}`}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Data Table Below Pie Chart */}
      <div className="grid grid-cols-2 gap-3">
        {data.map((item, index) => (
          <div key={index} className="p-2 bg-gray-50 dark:bg-gray-700 rounded-lg flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
            <div className="flex-1">
              <p className="text-xs text-gray-600 dark:text-gray-400">{item.name}</p>
              <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{formatWithGlobal(item.value)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Component: Spending Trend Chart
export const SpendingTrendChart = ({ data, viewType = '30days' }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-80 text-gray-400">
        <p>No spending data available</p>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis 
          dataKey={viewType === '30days' ? 'date' : viewType === 'yearly' ? 'year' : 'month'} 
          stroke="#6b7280" 
          angle={viewType === '30days' ? -45 : 0}
          textAnchor={viewType === '30days' ? 'end' : 'middle'}
          height={viewType === '30days' ? 80 : 30}
        />
        <YAxis stroke="#6b7280" />
        <Tooltip 
          formatter={(value) => formatCurrency(value)}
          labelFormatter={(label) => {
            if (viewType === '30days') return `Date: ${label}`
            if (viewType === 'yearly') return `Year: ${label}`
            return `Month: ${label}`
          }}
        />
        <Line 
          type="monotone" 
          dataKey="amount" 
          stroke="#3b82f6" 
          strokeWidth={2} 
          dot={{ fill: '#3b82f6', r: viewType === '30days' ? 3 : 5 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// Component: Budget Allocation vs Spent Chart
export const BudgetUtilizationChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-80 text-gray-400">
        <p>No budget data available</p>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis 
          dataKey="name" 
          stroke="#6b7280"
          angle={-45}
          textAnchor="end"
          height={80}
        />
        <YAxis stroke="#6b7280" />
        <Tooltip 
          formatter={(value) => formatCurrency(value)}
          labelFormatter={(label) => `Category: ${label}`}
        />
        <Legend 
          wrapperStyle={{ paddingTop: '20px' }}
          formatter={(value) => value === 'allocated' ? 'Budget Allocated' : 'Amount Spent'}
        />
        <Bar dataKey="allocated" fill="#10b981" name="allocated" />
        <Bar dataKey="spent" fill="#ef4444" name="spent" />
      </BarChart>
    </ResponsiveContainer>
  )
}
