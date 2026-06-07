/**
 * Dashboard Data Service Layer (SOLID: Single Responsibility)
 * Handles all data aggregation and calculations for dashboard components
 */
export class DashboardDataService {
  constructor(expenses = [], budgets = [], goals = [], loans = []) {
    // Ensure all data is arrays with proper defaults
    this.expenses = Array.isArray(expenses) ? expenses : (expenses?.data ? expenses.data : [])
    this.budgets = Array.isArray(budgets) ? budgets : (budgets?.data ? budgets.data : [])
    this.goals = Array.isArray(goals) ? goals : (goals?.data ? goals.data : [])
    this.loans = Array.isArray(loans) ? loans : (loans?.data ? loans.data : [])
    
    // Final safety check
    if (!Array.isArray(this.expenses)) this.expenses = []
    if (!Array.isArray(this.budgets)) this.budgets = []
    if (!Array.isArray(this.goals)) this.goals = []
    if (!Array.isArray(this.loans)) this.loans = []
  }

  // Stat calculations
  getStatistics() {
    try {
      // Calculate total recorded expenses from expense records (for reference)
      const expenseAmount = this.expenses.reduce((sum, e) => sum + (parseFloat(e?.amount) || 0), 0)
      
      // ✅ FIXED: Calculate total budget allocated (not recorded expenses)
      const budgetAmount = this.budgets.reduce((sum, b) => sum + (parseFloat(b?.allocated_amount) || 0), 0)
      
      // Calculate total EMI from loans (monthly commitment)
      const totalEMI = this.loans.reduce((sum, l) => sum + (parseFloat(l?.emi_amount) || 0), 0)
      
      // ✅ FIXED: Total monthly expenses = Budget Allocated + Loan EMI commitments
      const totalExpenses = budgetAmount + totalEMI
      
      return {
        totalExpenses: totalExpenses,
        budgetAmount: budgetAmount,
        recordedExpenses: expenseAmount,
        totalEMI: totalEMI,
        // Use allocated_amount (not amount) as budgets field name
        totalBudgets: this.budgets.reduce((sum, b) => sum + (parseFloat(b?.allocated_amount) || 0), 0),
        // Use spent_amount field instead of spent
        totalSpentOnBudgets: this.budgets.reduce((sum, b) => sum + (parseFloat(b?.spent_amount) || 0), 0),
        budgetAlerts: this.budgets.filter((b) => b?.alert).length,
        activeGoals: this.goals.filter((g) => !g?.completed).length,
        totalGoals: this.goals.length,
        totalLoans: this.loans.reduce((sum, l) => sum + (parseFloat(l?.principal_amount) || parseFloat(l?.amount) || 0), 0),
        activeLoans: this.loans.length,
      }
    } catch (error) {
      console.error('Error calculating statistics:', error)
      return {
        totalExpenses: 0,
        budgetAmount: 0,
        recordedExpenses: 0,
        totalEMI: 0,
        totalBudgets: 0,
        totalSpentOnBudgets: 0,
        budgetAlerts: 0,
        activeGoals: 0,
        totalGoals: 0,
        totalLoans: 0,
        activeLoans: 0,
      }
    }
  }

  // Expense breakdown by category (for pie chart)
  getExpensesByCategory() {
    try {
      const categoryMap = {}
      this.expenses.forEach((expense) => {
        const category = expense?.category || 'Other'
        const amount = parseFloat(expense?.amount) || 0
        categoryMap[category] = (categoryMap[category] || 0) + amount
      })
      return Object.entries(categoryMap).map(([name, value]) => ({
        name,
        value: parseFloat(value.toFixed(2)),
      }))
    } catch (error) {
      console.error('Error calculating expenses by category:', error)
      return []
    }
  }

  // Daily spending data for last 30 days
  getLast30DaysSpending() {
    try {
      const dailyMap = {}
      const today = new Date()
      
      // Initialize last 30 days
      for (let i = 29; i >= 0; i--) {
        const date = new Date(today)
        date.setDate(date.getDate() - i)
        const dateKey = date.toISOString().split('T')[0]
        dailyMap[dateKey] = 0
      }
      
      // Fill in actual expenses
      this.expenses.forEach((expense) => {
        const expenseDate = new Date(expense?.date)
        if (!isNaN(expenseDate)) {
          const dateKey = expenseDate.toISOString().split('T')[0]
          if (dailyMap[dateKey] !== undefined) {
            const amount = parseFloat(expense?.amount) || 0
            dailyMap[dateKey] = parseFloat((dailyMap[dateKey] + amount).toFixed(2))
          }
        }
      })
      
      return Object.entries(dailyMap).map(([date, amount]) => ({
        date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        amount: parseFloat(amount.toFixed(2)),
        fullDate: date,
      }))
    } catch (error) {
      console.error('Error calculating 30-day spending:', error)
      return []
    }
  }

  // Budget utilization - uses ACTUAL current month expenses, not budget.spent_amount
  getBudgetUtilization() {
    try {
      const today = new Date()
      const currentMonth = today.getMonth()
      const currentYear = today.getFullYear()

      // Map expenses by category for current month (normalize category names)
      const categoryExpensesMap = {}
      this.expenses.forEach((expense) => {
        const expenseDate = new Date(expense?.date)
        if (!isNaN(expenseDate) && 
            expenseDate.getMonth() === currentMonth && 
            expenseDate.getFullYear() === currentYear) {
          // Normalize category name to lowercase for consistent matching
          const category = (expense?.category || 'other').toLowerCase().trim()
          const amount = parseFloat(expense?.amount) || 0
          categoryExpensesMap[category] = (categoryExpensesMap[category] || 0) + amount
        }
      })

      // Filter budgets for current month only
      const monthKey = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}`
      const currentMonthBudgets = this.budgets.filter(b => {
        const budgetMonth = b?.month
        if (!budgetMonth) return false
        // Handle both string dates and Date objects
        const budgetMonthStr = typeof budgetMonth === 'string' 
          ? budgetMonth.substring(0, 7)
          : new Date(budgetMonth).toISOString().substring(0, 7)
        return budgetMonthStr === monthKey
      })

      return currentMonthBudgets.map((budget, index) => {
        // Use allocated_amount field (correct field name from backend)
        const allocated = parseFloat(budget?.allocated_amount) || 0
        // Normalize category name to lowercase for consistent matching
        const category = (budget?.category || 'Other').toLowerCase().trim()
        // Use ACTUAL expenses for this category in current month, not budget.spent_amount
        const spent = parseFloat((categoryExpensesMap[category] || 0).toFixed(2))
        const remaining = Math.max(0, allocated - spent)
        const percentage = allocated > 0 ? ((spent / allocated) * 100).toFixed(1) : 0
        
        return {
          id: budget?.id || `budget-${index}`,
          name: category,
          allocated: parseFloat(allocated.toFixed(2)),
          spent: parseFloat(spent.toFixed(2)),
          remaining: parseFloat(remaining.toFixed(2)),
          percentage: parseFloat(percentage),
          alertStatus: percentage >= 100 ? 'critical' : percentage >= 90 ? 'warning' : 'ok',
          isOverBudget: spent > allocated,
        }
      })
    } catch (error) {
      console.error('Error calculating budget utilization:', error)
      return []
    }
  }

  // Get this month's budget overview
  getCurrentMonthBudgetOverview() {
    try {
      const today = new Date()
      const currentMonth = today.getMonth()
      const currentYear = today.getFullYear()

      // Get current month expenses (ACTUAL SPENDING - not from budget data)
      const currentMonthExpenses = this.expenses.reduce((sum, expense) => {
        const expenseDate = new Date(expense?.date)
        if (!isNaN(expenseDate) && 
            expenseDate.getMonth() === currentMonth && 
            expenseDate.getFullYear() === currentYear) {
          return sum + (parseFloat(expense?.amount) || 0)
        }
        return sum
      }, 0)

      // Get this month's budgets for allocated amount only
      const monthKey = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}`
      const thisMonthBudgets = this.budgets.filter(b => b?.month?.startsWith(monthKey))
      
      // Use allocated_amount field (correct field name from backend)
      const totalAllocated = thisMonthBudgets.reduce((sum, b) => {
        return sum + (parseFloat(b?.allocated_amount) || 0)
      }, 0)

      // Use ACTUAL expenses for "spent" instead of budget.spent_amount
      const actualSpent = currentMonthExpenses
      const remaining = Math.max(0, totalAllocated - actualSpent)

      return {
        allocated: parseFloat(totalAllocated.toFixed(2)),
        spent: parseFloat(actualSpent.toFixed(2)),  // NOW uses actual expenses, not budget data
        remaining: parseFloat(remaining.toFixed(2)),
        percentage: totalAllocated > 0 ? ((actualSpent / totalAllocated) * 100).toFixed(1) : 0,
        monthExpenses: parseFloat(currentMonthExpenses.toFixed(2)),
      }
    } catch (error) {
      console.error('Error calculating current month budget overview:', error)
      return {
        allocated: 0,
        spent: 0,
        remaining: 0,
        percentage: 0,
        monthExpenses: 0,
      }
    }
  }

  // Goal progress
  getGoalProgress() {
    try {
      return this.goals.map((goal) => {
        const current = parseFloat(goal?.current_amount) || 0
        const target = parseFloat(goal?.target_amount) || 1
        const percentage = (current / target) * 100
        return {
          name: goal?.goal_name || goal?.name || 'Unnamed Goal',
          current: parseFloat(current.toFixed(2)),
          target: parseFloat(target.toFixed(2)),
          percentage: Math.min(percentage, 100),
        }
      })
    } catch (error) {
      console.error('Error calculating goal progress:', error)
      return []
    }
  }
}
