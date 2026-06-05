/**
 * DashboardPage — strict TypeScript, authenticated overview page.
 *
 * Responsibilities (SRP):
 *  - Guard route via useProtectedRoute
 *  - Fetch all domain data once, refetch on tab-focus
 *  - Delegate rendering to OverviewTab
 */

import React, { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Plus, BarChart3, Home } from 'lucide-react'

import { Layout, PageContainer } from '../components/Layout'
import { Button, LoadingSpinner, FluidIcon } from '../components/UI'
import { useProtectedRoute } from '../hooks/useAuth'
import {
  useExpenseStore,
  useBudgetStore,
  useGoalStore,
  useLoanStore,
} from '../store/index'
import { useAuthStore } from '../store/authStore'
import { OverviewTab } from '../components/dashboard/OverviewTab'

// OverviewTab is a JSX component without TS declarations — bridge with any
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const OverviewTabBridge = OverviewTab as React.ComponentType<Record<string, unknown>>


// ── Types ──────────────────────────────────────────────────────────────────

interface DashboardActionBarProps {
  onAddExpense: () => void
  onViewReports: () => void
}

// ── Sub-components ─────────────────────────────────────────────────────────

const DashboardActionBar: React.FC<DashboardActionBarProps> = ({ onAddExpense, onViewReports }) => (
  <div className="flex gap-2">
    <Button onClick={onAddExpense} variant="primary" className="gap-2">
      <FluidIcon icon={Plus} size="sm" className="text-white" />
      Add Expense
    </Button>
    <Button onClick={onViewReports} variant="secondary" className="gap-2" title="View reports and export data">
      <FluidIcon icon={BarChart3} size="sm" className="text-primary-600 dark:text-primary-400" />
      Reports
    </Button>
  </div>
)

// ── Main component ─────────────────────────────────────────────────────────

export const DashboardPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const dataFetchedRef = useRef(false)

  const { expenses, fetchExpenses, isLoading: expensesLoading } = useExpenseStore()
  const { budgets, fetchBudgets, isLoading: budgetsLoading } = useBudgetStore()
  const { goals, fetchGoals, isLoading: goalsLoading } = useGoalStore()
  const { loans, fetchLoans, isLoading: loansLoading } = useLoanStore()

  // Fetch once on first authentication
  useEffect(() => {
    if (isAuthenticated && !dataFetchedRef.current) {
      dataFetchedRef.current = true
      Promise.allSettled([fetchExpenses(), fetchBudgets(), fetchGoals(), fetchLoans()]).catch(
        (err) => console.error('Dashboard data fetch error:', err)
      )
    }
  }, [isAuthenticated, fetchExpenses, fetchBudgets, fetchGoals, fetchLoans])

  // Refetch on tab visibility change (real-time feel)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        Promise.allSettled([fetchExpenses(), fetchBudgets(), fetchGoals(), fetchLoans()]).catch(
          (err) => console.error('Dashboard refetch error:', err)
        )
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [fetchExpenses, fetchBudgets, fetchGoals, fetchLoans])

  const isDataLoading = expensesLoading || budgetsLoading || goalsLoading || loansLoading

  if (!isAuthenticated || isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
          <LoadingSpinner size="lg" />
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageContainer
        title={`Welcome back, ${user?.name ?? 'User'}!`}
        subtitle="Manage your finances with detailed insights"
        icon={Home}
        showLogo
        action={
          <DashboardActionBar
            onAddExpense={() => navigate('/expenses')}
            onViewReports={() => navigate('/reports')}
          />
        }
      >
        {isDataLoading ? (
          <motion.div
            className="flex items-center justify-center"
            style={{ minHeight: 'var(--placeholder-height)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <LoadingSpinner size="lg" />
          </motion.div>
        ) : (
        <OverviewTabBridge
            expenses={[...expenses]}
            budgets={[...budgets]}
            goals={[...goals]}
            loans={[...loans]}
          />
        )}
      </PageContainer>
    </Layout>
  )
}
