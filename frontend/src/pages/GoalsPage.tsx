/**
 * GoalsPage — financial goals with progress tracking.
 *
 * Responsibilities (SRP):
 *  - Guard route via useProtectedRoute
 *  - CRUD + addProgress via useGoalStore
 *  - Derive completion % and status reactively
 */

import React, { useEffect, useState, useMemo, useRef, useCallback, type FormEvent, type ChangeEvent } from 'react'
import { motion } from 'framer-motion'
import { Target, Plus, Edit2, Trash2, TrendingUp } from 'lucide-react'

import { Layout, PageContainer } from '@/components/Layout'
import { Button, Input, Select, LoadingSpinner, EmptyState, Modal, FluidIcon } from '@/components/UI'
import { FluidGrid } from '@/components/FluidGrid'
import { useProtectedRoute } from '@/hooks/useAuth'
import { useCurrency } from '@/hooks/useCurrency'
import { useGoalStore } from '@/store/index'
import { showSuccessToast, showErrorToast } from '@/utils/toast'
import type { Goal, GoalStatus } from '@/types'

// ── Types ──────────────────────────────────────────────────────────────────

interface GoalFormData {
  title: string
  description: string
  target_amount: string
  current_amount: string
  deadline: string
}

type GoalFormErrors = Partial<Record<keyof GoalFormData, string>>

// ── Helpers ────────────────────────────────────────────────────────────────

const goalPct = (g: Goal): number => {
  if (g.target_amount <= 0) return 0
  return Math.min((g.current_amount / g.target_amount) * 100, 100)
}

const STATUS_LABELS: Record<GoalStatus, string> = {
  active: 'Active',
  completed: 'Completed',
  paused: 'Paused',
  cancelled: 'Cancelled',
}

const STATUS_COLORS: Record<GoalStatus, string> = {
  active: 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30',
  completed: 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30',
  paused: 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30',
  cancelled: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
}

const STATUS_OPTIONS = Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))

// ── Sub-components ─────────────────────────────────────────────────────────

interface SummaryCardProps {
  label: string
  value: string
  subtext: string
  colorClass: string
  gradientClass: string
}

const SummaryCard: React.FC<SummaryCardProps> = ({ label, value, subtext, colorClass, gradientClass }) => (
  <motion.div
    className={`p-4 sm:p-6 ${gradientClass} rounded-lg border-l-4 ${colorClass}`}
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
  >
    <p className="text-gray-600 dark:text-gray-400 text-sm-fluid mb-2">{label}</p>
    <p className={`text-value font-bold ${colorClass.replace('border-', 'text-')}`}>{value}</p>
    <p className="text-gray-600 dark:text-gray-400 text-xs-fluid sm:text-sm-fluid mt-2">{subtext}</p>
  </motion.div>
)

interface GoalProgressBarProps {
  pct: number
  status: GoalStatus
}

const GoalProgressBar: React.FC<GoalProgressBarProps> = ({ pct, status }) => {
  const color = status === 'completed' ? 'bg-blue-500' : status === 'paused' ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-2">
      <div className={`h-2 rounded-full transition-all duration-700 ${color}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export const GoalsPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { formatCurrency } = useCurrency()
  const dataFetchedRef = useRef(false)

  const { goals, fetchGoals, createGoal, updateGoal, deleteGoal, addProgress, isLoading: goalsLoading } = useGoalStore()

  const [filterStatus, setFilterStatus] = useState<string>('active')
  const [isModalOpen, setIsModalOpen]   = useState(false)
  const [isProgressOpen, setIsProgressOpen] = useState(false)
  const [editingId, setEditingId]       = useState<number | null>(null)
  const [progressGoalId, setProgressGoalId] = useState<number | null>(null)
  const [progressAmount, setProgressAmount] = useState('')
  const [formData, setFormData]         = useState<GoalFormData>({
    title: '', description: '', target_amount: '', current_amount: '0',
    deadline: '',
  })
  const [formErrors, setFormErrors]     = useState<GoalFormErrors>({})

  useEffect(() => {
    if (isAuthenticated && !dataFetchedRef.current) {
      dataFetchedRef.current = true
      fetchGoals().catch(console.error)
    }
  }, [isAuthenticated, fetchGoals])

  // ── Derived data ───────────────────────────────────────────────────────

  const filteredGoals = useMemo(() =>
    filterStatus === 'all' ? [...goals] : goals.filter((g) => g.status === filterStatus),
    [goals, filterStatus],
  )

  const summary = useMemo(() => {
    const all = goals
    const active     = all.filter((g) => g.status === 'active').length
    const completed  = all.filter((g) => g.status === 'completed').length
    const totalTarget = all.reduce((s, g) => s + g.target_amount, 0)
    const totalSaved  = all.reduce((s, g) => s + g.current_amount, 0)
    return { active, completed, totalTarget, totalSaved }
  }, [goals])

  // ── Handlers ───────────────────────────────────────────────────────────

  const validateForm = useCallback((): GoalFormErrors => {
    const errors: GoalFormErrors = {}
    if (!formData.title.trim()) errors.title = 'Title is required'
    if (!formData.target_amount) errors.target_amount = 'Target amount is required'
    else if (parseFloat(formData.target_amount) <= 0) errors.target_amount = 'Must be positive'
    return errors
  }, [formData])

  const resetForm = useCallback(() => {
    setFormData({ title: '', description: '', target_amount: '', current_amount: '0', deadline: '' })
    setFormErrors({})
    setEditingId(null)
  }, [])

  const handleSubmit = useCallback(async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const errors = validateForm()
    if (Object.keys(errors).length > 0) { setFormErrors(errors); return }

    const payload = {
      title: formData.title.trim(),
      description: formData.description.trim() || undefined,
      target_amount: parseFloat(formData.target_amount),
      current_amount: parseFloat(formData.current_amount) || 0,
      deadline: formData.deadline || undefined,
    }

    try {
      if (editingId !== null) {
        await updateGoal(editingId, payload)
        showSuccessToast('Goal updated')
      } else {
        await createGoal(payload)
        showSuccessToast('Goal created')
      }
      setIsModalOpen(false)
      resetForm()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail ?? 'Unknown error'
      showErrorToast(editingId !== null ? `Update failed: ${msg}` : `Create failed: ${msg}`)
    }
  }, [formData, validateForm, editingId, updateGoal, createGoal, resetForm])

  const handleEdit = useCallback((goal: Goal) => {
    setEditingId(goal.id)
    setFormData({
      title: goal.title,
      description: goal.description ?? '',
      target_amount: String(goal.target_amount),
      current_amount: String(goal.current_amount),
      deadline: goal.deadline?.split('T')[0] ?? '',
    })
    setIsModalOpen(true)
  }, [])

  const handleDelete = useCallback(async (id: number) => {
    if (!window.confirm('Delete this goal?')) return
    try {
      await deleteGoal(id)
      showSuccessToast('Goal deleted')
    } catch {
      showErrorToast('Failed to delete goal')
    }
  }, [deleteGoal])

  const openProgress = useCallback((id: number) => {
    setProgressGoalId(id)
    setProgressAmount('')
    setIsProgressOpen(true)
  }, [])

  const handleAddProgress = useCallback(async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!progressGoalId) return
    const amount = parseFloat(progressAmount)
    if (!amount || amount <= 0) { showErrorToast('Enter a valid positive amount'); return }
    try {
      await addProgress(progressGoalId, amount)
      showSuccessToast('Progress added!')
      setIsProgressOpen(false)
    } catch {
      showErrorToast('Failed to add progress')
    }
  }, [progressGoalId, progressAmount, addProgress])

  const field = useCallback(
    (key: keyof GoalFormData) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      setFormData((p) => ({ ...p, [key]: e.target.value }))
      setFormErrors((p) => ({ ...p, [key]: '' }))
    }, [],
  )

  // ── Guard ──────────────────────────────────────────────────────────────

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
      <PageContainer title="Goals" subtitle="Set and track your savings goals" icon={Target}>

        {/* Filter */}
        <motion.div className="flex gap-4 mb-6 flex-wrap items-end" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="w-52">
            <Select label="Status" options={[{ value: 'all', label: 'All Statuses' }, ...STATUS_OPTIONS]}
              value={filterStatus}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilterStatus(e.target.value)} />
          </div>
        </motion.div>

        {/* Summary Cards */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6">
          <FluidGrid min="200px" className="gap-4">
            <SummaryCard label="Active Goals" value={String(summary.active)}
              subtext={`${summary.completed} completed`}
              colorClass="border-green-500"
              gradientClass="bg-gradient-to-r from-green-50 to-teal-50 dark:from-green-900/30 dark:to-teal-900/30" />
            <SummaryCard label="Total Target" value={formatCurrency(summary.totalTarget)}
              subtext="across all goals"
              colorClass="border-blue-500"
              gradientClass="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30" />
            <SummaryCard label="Total Saved" value={formatCurrency(summary.totalSaved)}
              subtext={`${summary.totalTarget > 0 ? ((summary.totalSaved / summary.totalTarget) * 100).toFixed(0) : 0}% of total target`}
              colorClass="border-purple-500"
              gradientClass="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/30 dark:to-pink-900/30" />
          </FluidGrid>
        </motion.div>

        {/* Add CTA */}
        <div className="flex justify-end mb-4">
          <Button onClick={() => { resetForm(); setIsModalOpen(true) }} variant="primary" className="gap-2">
            <FluidIcon icon={Plus} size="sm" />
            New Goal
          </Button>
        </div>

        {/* Goal List */}
        {goalsLoading ? (
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        ) : filteredGoals.length === 0 ? (
          <EmptyState icon={Target} title="No goals found"
            description={filterStatus === 'all' ? 'Create your first savings goal' : `No ${filterStatus} goals`}
            action={<Button onClick={() => { resetForm(); setIsModalOpen(true) }} variant="primary">Create Goal</Button>} />
        ) : (
          <motion.div className="space-y-4" role="list" aria-label="Goals list">
            {filteredGoals.map((goal, i) => {
              const pct = goalPct(goal)
              const remaining = Math.max(goal.target_amount - goal.current_amount, 0)

              return (
                <motion.div key={goal.id} role="listitem"
                  className="glass rounded-lg p-4 sm:p-6 hover:shadow-card-hover"
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }} whileHover={{ x: 3 }}>

                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">{goal.title}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[goal.status]}`}>
                          {STATUS_LABELS[goal.status]}
                        </span>
                      </div>
                      {goal.description && (
                        <p className="text-sm-fluid text-gray-500 dark:text-gray-400 mb-1">{goal.description}</p>
                      )}
                      {goal.deadline && (
                        <p className="text-xs-fluid text-gray-400 dark:text-gray-500 mb-1">
                          Deadline: {new Date(goal.deadline).toLocaleDateString()}
                        </p>
                      )}
                      <GoalProgressBar pct={pct} status={goal.status} />
                      <div className="flex justify-between mt-1 text-xs-fluid text-gray-500 dark:text-gray-400">
                        <span>{formatCurrency(goal.current_amount)} saved</span>
                        <span>{pct.toFixed(0)}% — {formatCurrency(remaining)} remaining</span>
                      </div>
                    </div>

                    <div className="flex gap-2 flex-shrink-0 flex-col sm:flex-row">
                      {goal.status === 'active' && (
                        <Button size="sm" variant="ghost" className="p-2 text-green-600" onClick={() => openProgress(goal.id)} title="Add progress">
                          <FluidIcon icon={TrendingUp} size="sm" />
                        </Button>
                      )}
                      <Button size="sm" variant="ghost" className="p-2" onClick={() => handleEdit(goal)} title="Edit">
                        <FluidIcon icon={Edit2} size="sm" />
                      </Button>
                      <Button size="sm" variant="ghost" className="p-2 text-red-600" onClick={() => handleDelete(goal.id)} title="Delete">
                        <FluidIcon icon={Trash2} size="sm" />
                      </Button>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </motion.div>
        )}
      </PageContainer>

      {/* Create / Edit Modal */}
      <Modal isOpen={isModalOpen} onClose={() => { setIsModalOpen(false); resetForm() }}
        title={editingId !== null ? 'Edit Goal' : 'New Goal'} className="max-w-sm">
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Input label="Title" type="text" placeholder="e.g., Emergency Fund"
            value={formData.title} onChange={field('title') as (e: ChangeEvent<HTMLInputElement>) => void}
            error={formErrors.title} />
          <Input label="Description (optional)" type="text" placeholder="Short description"
            value={formData.description} onChange={field('description') as (e: ChangeEvent<HTMLInputElement>) => void} />
          <Input label="Target Amount ($)" type="number" placeholder="0.00" step="0.01"
            value={formData.target_amount} onChange={field('target_amount') as (e: ChangeEvent<HTMLInputElement>) => void}
            error={formErrors.target_amount} />
          <Input label="Starting Amount ($)" type="number" placeholder="0.00" step="0.01"
            value={formData.current_amount} onChange={field('current_amount') as (e: ChangeEvent<HTMLInputElement>) => void} />
          <Input label="Deadline (optional)" type="date"
            value={formData.deadline} onChange={field('deadline') as (e: ChangeEvent<HTMLInputElement>) => void} />
          <div className="flex gap-3 pt-4">
            <Button type="submit" variant="primary" className="flex-1" isLoading={goalsLoading}>
              {editingId !== null ? 'Update' : 'Create'} Goal
            </Button>
            <Button type="button" variant="secondary" className="flex-1"
              onClick={() => { setIsModalOpen(false); resetForm() }}>
              Cancel
            </Button>
          </div>
        </form>
      </Modal>

      {/* Add Progress Modal */}
      <Modal isOpen={isProgressOpen} onClose={() => setIsProgressOpen(false)}
        title="Add Progress" className="max-w-xs">
        <form onSubmit={handleAddProgress} className="space-y-4" noValidate>
          <Input label="Amount to Add ($)" type="number" placeholder="0.00" step="0.01"
            value={progressAmount}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setProgressAmount(e.target.value)} />
          <div className="flex gap-3 pt-2">
            <Button type="submit" variant="primary" className="flex-1" isLoading={goalsLoading}>
              Add
            </Button>
            <Button type="button" variant="secondary" className="flex-1"
              onClick={() => setIsProgressOpen(false)}>
              Cancel
            </Button>
          </div>
        </form>
      </Modal>
    </Layout>
  )
}
