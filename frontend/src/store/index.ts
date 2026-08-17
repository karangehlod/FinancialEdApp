/**
 * Store barrel — re-exports all domain stores.
 * Import from '@/store/index' (or '@/store') as before; individual
 * store files can also be imported directly for better tree-shaking.
 */

export { useProfileStore }      from './profileStore'
export { useExpenseStore }      from './expenseStore'
export { useBudgetStore }       from './budgetStore'
export { useGoalStore }         from './goalStore'
export { useLoanStore }         from './loanStore'
export { useNotificationStore } from './notificationStore'
