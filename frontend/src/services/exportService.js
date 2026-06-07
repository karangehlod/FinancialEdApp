/**
 * Export Service - Handle CSV and JSON exports
 */

export const exportService = {
  // Export data as CSV
  exportToCSV: (filename, data, headers = []) => {
    try {
      if (!data || data.length === 0) {
        console.warn('No data to export')
        return
      }

      // Determine headers if not provided
      const csvHeaders = headers.length > 0 ? headers : Object.keys(data[0])
      
      // Create CSV content
      const csvContent = [
        csvHeaders.join(','),
        ...data.map(row =>
          csvHeaders.map(header => {
            const value = row[header]
            // Escape quotes and wrap in quotes if contains comma or newline
            if (typeof value === 'string' && (value.includes(',') || value.includes('\n') || value.includes('"'))) {
              return `"${value.replace(/"/g, '""')}"`
            }
            return value
          }).join(',')
        )
      ].join('\n')

      // Create blob and download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.setAttribute('href', URL.createObjectURL(blob))
      link.setAttribute('download', `${filename}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      return true
    } catch (error) {
      console.error('Error exporting to CSV:', error)
      return false
    }
  },

  // Export data as JSON
  exportToJSON: (filename, data) => {
    try {
      if (!data) {
        console.warn('No data to export')
        return false
      }

      const jsonContent = JSON.stringify(data, null, 2)
      const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' })
      const link = document.createElement('a')
      link.setAttribute('href', URL.createObjectURL(blob))
      link.setAttribute('download', `${filename}.json`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      return true
    } catch (error) {
      console.error('Error exporting to JSON:', error)
      return false
    }
  },

  // Export expenses as CSV
  exportExpensesCSV: (expenses, filename = 'expenses') => {
    const data = expenses.map(expense => ({
      Date: new Date(expense.date).toLocaleDateString(),
      Description: expense.description,
      Category: expense.category,
      Amount: expense.amount,
    }))
    return exportService.exportToCSV(filename, data)
  },

  // Export budgets as CSV
  exportBudgetsCSV: (budgets, filename = 'budgets') => {
    const data = budgets.map(budget => ({
      Month: budget.month || 'N/A',
      Category: budget.category,
      'Allocated Amount': budget.allocated_amount || budget.amount,
      'Spent Amount': budget.spent_amount || budget.spent || 0,
      Remaining: (budget.allocated_amount || budget.amount) - (budget.spent_amount || budget.spent || 0),
      'Utilization %': budget.percentage || 0,
    }))
    return exportService.exportToCSV(filename, data)
  },

  // Export goals as CSV
  exportGoalsCSV: (goals, filename = 'goals') => {
    const data = goals.map(goal => ({
      'Goal Name': goal.goal_name || goal.name,
      'Goal Type': goal.goal_type || 'N/A',
      'Target Amount': goal.target_amount,
      'Current Amount': goal.current_amount,
      'Target Date': goal.target_date || goal.deadline || 'N/A',
      Progress: goal.progress_percentage ? `${goal.progress_percentage.toFixed(1)}%` : '0%',
      Status: goal.status || 'Active',
      Priority: goal.priority || 'N/A',
    }))
    return exportService.exportToCSV(filename, data)
  },

  // Export dashboard summary as JSON
  exportDashboardSummary: (stats, expenses, budgets, goals, filename = 'dashboard-summary') => {
    const data = {
      exportDate: new Date().toISOString(),
      summary: stats,
      expensesByCategory: expenses
        .reduce((acc, exp) => {
          const cat = exp.category || 'Other'
          acc[cat] = (acc[cat] || 0) + exp.amount
          return acc
        }, {}),
      budgetUtilization: budgets.map(b => ({
        category: b.category,
        allocated: b.allocated_amount || b.amount,
        spent: b.spent_amount || b.spent,
        percentage: ((b.spent_amount || b.spent || 0) / (b.allocated_amount || b.amount || 1)) * 100,
      })),
      goalsProgress: goals.map(g => ({
        name: g.goal_name || g.name,
        target: g.target_amount,
        current: g.current_amount,
        progress: ((g.current_amount || 0) / (g.target_amount || 1)) * 100,
      })),
      totalExpenses: expenses.length,
      totalBudgets: budgets.length,
      totalGoals: goals.length,
    }
    return exportService.exportToJSON(filename, data)
  },
}
