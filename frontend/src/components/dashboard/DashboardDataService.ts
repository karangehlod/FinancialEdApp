export type RawExpense = { amount?: number | string; date?: string; category?: string }
export type RawBudget = { allocated_amount?: number | string; month?: string; category?: string; id?: number; spent_amount?: number | string; alert?: boolean }
export type RawGoal = { current_amount?: number | string; target_amount?: number | string; goal_name?: string; name?: string; completed?: boolean }
export type RawLoan = { emi_amount?: number | string; principal_amount?: number | string; amount?: number | string }

export class DashboardDataService {
  expenses: RawExpense[]
  budgets: RawBudget[]
  goals: RawGoal[]
  loans: RawLoan[]

  constructor(expenses: any = [], budgets: any = [], goals: any = [], loans: any = []) {
    this.expenses = Array.isArray(expenses) ? expenses : (expenses?.data ?? [])
    this.budgets = Array.isArray(budgets) ? budgets : (budgets?.data ?? [])
    this.goals = Array.isArray(goals) ? goals : (goals?.data ?? [])
    this.loans = Array.isArray(loans) ? loans : (loans?.data ?? [])

    if (!Array.isArray(this.expenses)) this.expenses = []
    if (!Array.isArray(this.budgets)) this.budgets = []
    if (!Array.isArray(this.goals)) this.goals = []
    if (!Array.isArray(this.loans)) this.loans = []
  }

  getStatistics() {
    try {
      const expenseAmount = this.expenses.reduce((sum, e) => sum + (parseFloat(String(e?.amount)) || 0), 0)
      const budgetAmount = this.budgets.reduce((sum, b) => sum + (parseFloat(String(b?.allocated_amount)) || 0), 0)
      const totalEMI = this.loans.reduce((sum, l) => sum + (parseFloat(String(l?.emi_amount)) || 0), 0)
      const totalExpenses = budgetAmount + totalEMI

      return {
        totalExpenses,
        budgetAmount,
        recordedExpenses: expenseAmount,
        totalEMI,
        totalBudgets: this.budgets.reduce((sum, b) => sum + (parseFloat(String(b?.allocated_amount)) || 0), 0),
        totalSpentOnBudgets: this.budgets.reduce((sum, b) => sum + (parseFloat(String(b?.spent_amount)) || 0), 0),
        budgetAlerts: this.budgets.filter((b) => Boolean(b?.alert)).length,
        activeGoals: this.goals.filter((g) => !(g as any)?.completed).length,
        totalGoals: this.goals.length,
        totalLoans: this.loans.reduce((sum, l) => sum + (parseFloat(String(l?.principal_amount)) || parseFloat(String(l?.amount)) || 0), 0),
        activeLoans: this.loans.length,
      }
    } catch (err) {
      // log and return safe defaults
      // eslint-disable-next-line no-console
      console.error('DashboardDataService.getStatistics error', err)
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

  getExpensesByCategory() {
    try {
      const categoryMap: Record<string, number> = {}
      this.expenses.forEach((expense) => {
        const category = (expense?.category as string) || 'Other'
        const amount = parseFloat(String(expense?.amount)) || 0
        categoryMap[category] = (categoryMap[category] || 0) + amount
      })
      return Object.entries(categoryMap).map(([name, value]) => ({ name, value: parseFloat(value.toFixed(2)) }))
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('DashboardDataService.getExpensesByCategory error', err)
      return [] as Array<{ name: string; value: number }>
    }
  }

  getLast30DaysSpending() {
    try {
      const dailyMap: Record<string, number> = {}
      const today = new Date()
      for (let i = 29; i >= 0; i--) {
        const date = new Date(today)
        date.setDate(date.getDate() - i)
        const dateKey = date.toISOString().split('T')[0]
        dailyMap[dateKey] = 0
      }

      this.expenses.forEach((expense) => {
        const dstr = expense?.date
        if (!dstr) return
        const expenseDate = new Date(dstr)
        if (isNaN(expenseDate.getTime())) return
        const dateKey = expenseDate.toISOString().split('T')[0]
        if (dailyMap[dateKey] !== undefined) {
          const amount = parseFloat(String(expense?.amount)) || 0
          dailyMap[dateKey] = parseFloat((dailyMap[dateKey] + amount).toFixed(2))
        }
      })

      return Object.entries(dailyMap).map(([date, amount]) => ({
        date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        amount: parseFloat(amount.toFixed(2)),
        fullDate: date,
      }))
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('DashboardDataService.getLast30DaysSpending error', err)
      return [] as Array<{ date: string; amount: number; fullDate: string }>
    }
  }

  getBudgetUtilization() {
    try {
      const today = new Date()
      const currentMonth = today.getMonth()
      const currentYear = today.getFullYear()

      const categoryExpensesMap: Record<string, number> = {}
      this.expenses.forEach((expense) => {
        const dstr = expense?.date
        if (!dstr) return
        const expenseDate = new Date(dstr)
        if (isNaN(expenseDate.getTime())) return
        if (expenseDate.getMonth() === currentMonth && expenseDate.getFullYear() === currentYear) {
          const category = (expense?.category || 'other').toString().toLowerCase().trim()
          const amount = parseFloat(String(expense?.amount)) || 0
          categoryExpensesMap[category] = (categoryExpensesMap[category] || 0) + amount
        }
      })

      const monthKey = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}`
      const currentMonthBudgets = this.budgets.filter((b) => {
        const budgetMonth = b?.month
        if (!budgetMonth) return false
        const budgetMonthStr = typeof budgetMonth === 'string' ? budgetMonth.substring(0, 7) : new Date(budgetMonth).toISOString().substring(0, 7)
        return budgetMonthStr === monthKey
      })

      return currentMonthBudgets.map((budget, index) => {
        const allocated = parseFloat(String(budget?.allocated_amount)) || 0
        const category = (budget?.category || 'other').toString().toLowerCase().trim()
        const spent = parseFloat(String(categoryExpensesMap[category] || 0)) || 0
        const remaining = Math.max(0, allocated - spent)
        const percentage = allocated > 0 ? parseFloat(((spent / allocated) * 100).toFixed(1)) : 0
        return {
          id: (budget?.id as any) || `budget-${index}`,
          name: category,
          allocated: parseFloat(allocated.toFixed(2)),
          spent: parseFloat(spent.toFixed(2)),
          remaining: parseFloat(remaining.toFixed(2)),
          percentage,
          alertStatus: percentage >= 100 ? 'critical' : percentage >= 90 ? 'warning' : 'ok',
          isOverBudget: spent > allocated,
        }
      })
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('DashboardDataService.getBudgetUtilization error', err)
      return [] as Array<any>
    }
  }

  getCurrentMonthBudgetOverview() {
    try {
      const today = new Date()
      const currentMonth = today.getMonth()
      const currentYear = today.getFullYear()

      const currentMonthExpenses = this.expenses.reduce((sum, expense) => {
        const dstr = expense?.date
        if (!dstr) return sum
        const expenseDate = new Date(dstr)
        if (isNaN(expenseDate.getTime())) return sum
        if (expenseDate.getMonth() === currentMonth && expenseDate.getFullYear() === currentYear) {
          return sum + (parseFloat(String(expense?.amount)) || 0)
        }
        return sum
      }, 0)

      const monthKey = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}`
      const thisMonthBudgets = this.budgets.filter((b) => (b?.month || '').toString().startsWith(monthKey))

      const totalAllocated = thisMonthBudgets.reduce((sum, b) => sum + (parseFloat(String(b?.allocated_amount)) || 0), 0)
      const actualSpent = currentMonthExpenses
      const remaining = Math.max(0, totalAllocated - actualSpent)

      return {
        allocated: parseFloat(totalAllocated.toFixed(2)),
        spent: parseFloat(actualSpent.toFixed(2)),
        remaining: parseFloat(remaining.toFixed(2)),
        percentage: totalAllocated > 0 ? parseFloat(((actualSpent / totalAllocated) * 100).toFixed(1)) : 0,
        monthExpenses: parseFloat(currentMonthExpenses.toFixed(2)),
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('DashboardDataService.getCurrentMonthBudgetOverview error', err)
      return { allocated: 0, spent: 0, remaining: 0, percentage: 0, monthExpenses: 0 }
    }
  }

  getGoalProgress() {
    try {
      return this.goals.map((goal) => {
        const current = parseFloat(String(goal?.current_amount)) || 0
        const target = parseFloat(String(goal?.target_amount)) || 1
        const percentage = (current / target) * 100
        return {
          name: goal?.goal_name || goal?.name || 'Unnamed Goal',
          current: parseFloat(current.toFixed(2)),
          target: parseFloat(target.toFixed(2)),
          percentage: Math.min(percentage, 100),
        }
      })
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('DashboardDataService.getGoalProgress error', err)
      return [] as Array<any>
    }
  }
}
