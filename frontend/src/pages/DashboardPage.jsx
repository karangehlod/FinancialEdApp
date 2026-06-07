import React, { useEffect, useRef } from 'react'
import { Layout, PageContainer } from '../components/Layout'
import { useProtectedRoute } from '../hooks/useAuth'
import { Button, LoadingSpinner } from '../components/UI'
import {
  useExpenseStore,
  useBudgetStore,
  useGoalStore,
  useLoanStore,
} from '../store/index'
import { useAuthStore } from '../store/authStore'
import { motion } from 'framer-motion'
import {
  Plus,
  BarChart3,
  Home,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

// Import overview component
import { OverviewTab } from '../components/dashboard/OverviewTab'

export const DashboardPage = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const dataFetchedRef = useRef(false)

  // Store hooks
  const { expenses = [], fetchExpenses, isLoading: expensesLoading } = useExpenseStore()
  const { budgets = [], fetchBudgets, isLoading: budgetsLoading } = useBudgetStore()
  const { goals = [], fetchGoals, isLoading: goalsLoading } = useGoalStore()
  const { loans = [], fetchLoans, isLoading: loansLoading } = useLoanStore()

  // ===== DATA FETCHING - Only fetch once when authenticated =====
  useEffect(() => {
    if (isAuthenticated && !dataFetchedRef.current) {
      dataFetchedRef.current = true
      try {
        fetchExpenses()
        fetchBudgets()
        fetchGoals()
        fetchLoans()
      } catch (err) {
        console.error('Error fetching dashboard data:', err)
      }
    }
  }, [isAuthenticated])

  // ===== REAL-TIME UPDATES - Refetch when page focus returns =====
  useEffect(() => {
    const handlePageFocus = () => {
      try {
        // logger.info('Dashboard page focused - refetching data for real-time updates')
        fetchExpenses()
        fetchBudgets()
        fetchGoals()
        fetchLoans()
      } catch (err) {
        console.error('Error refetching dashboard data:', err)
      }
    }

    // Listen for page visibility changes (user returns to tab)
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        handlePageFocus()
      }
    })

    // Cleanup
    return () => {
      document.removeEventListener('visibilitychange', handlePageFocus)
    }
  }, [fetchExpenses, fetchBudgets, fetchGoals, fetchLoans])

  const isLoading_ = expensesLoading || budgetsLoading || goalsLoading || loansLoading

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
        title={`Welcome back, ${user?.name || 'User'}!`}
        subtitle="Manage your finances with detailed insights"
        icon={Home}
        iconSize={'var(--page-icon-size)'}
        showLogo={true}
        action={
          <div className="flex gap-2">
            <Button
              onClick={() => navigate('/expenses')}
              variant="primary"
              className="gap-2"
            >
              <Plus size={20} />
              Add Expense
            </Button>
            <Button
              onClick={() => navigate('/reports')}
              variant="secondary"
              className="gap-2"
              title="View reports and export data"
            >
              <BarChart3 size={20} />
              Reports
            </Button>
          </div>
        }
      >
        {/* Loading State */}
        {isLoading_ && (
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        )}

        {/* Overview Content */}
        {!isLoading_ && (
          <OverviewTab 
            expenses={expenses}
            budgets={budgets}
            goals={goals}
            loans={loans}
          />
        )}
      </PageContainer>
    </Layout>
  )
}
