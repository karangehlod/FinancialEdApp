import React, { useState, useEffect, useCallback } from 'react'
import { Layout, PageContainer } from '../components/Layout'
import { Card, Button, Input, LoadingSpinner } from '../components/UI'
import { useProtectedRoute } from '../hooks/useAuth'
import { adminService } from '../services/apiService'
import { showErrorToast, showSuccessToast } from '../utils/toast'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Users, Activity, Shield, AlertTriangle, Search, RefreshCw,
  ChevronLeft, ChevronRight, Ban, CheckCircle, Server, Database,
  TrendingUp, UserPlus, BarChart3,
} from 'lucide-react'

/* ── Metric Card ───────────────────────────────────────────────────────── */
const MetricCard = ({ icon: Icon, label, value, color = 'blue', subtitle }) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm"
  >
    <div className="flex items-center gap-3">
      <div className={`p-3 rounded-lg bg-${color}-100 dark:bg-${color}-900/30`}>
        <Icon style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)', color: `var(--${color}-600, #000)` }} />
      </div>
      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{value ?? '—'}</p>
        {subtitle && <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  </motion.div>
)

/* ── Status Badge ──────────────────────────────────────────────────────── */
const StatusBadge = ({ active, verified }) => (
  <div className="flex gap-1.5">
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
      active
        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
        : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
    }`}>
      {active ? 'Active' : 'Suspended'}
    </span>
    {verified && (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
        Verified
      </span>
    )}
  </div>
)

/* ── Main Admin Page ───────────────────────────────────────────────────── */
export const AdminPage = () => {
  const { isAuthenticated, isLoading: authLoading } = useProtectedRoute()

  const [activeTab, setActiveTab] = useState('overview')
  const [metrics, setMetrics] = useState(null)
  const [users, setUsers] = useState([])
  const [usersPagination, setUsersPagination] = useState({ total: 0, page: 1, pages: 1, per_page: 20 })
  const [health, setHealth] = useState(null)
  const [auditLog, setAuditLog] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  /* ── Fetch helpers ─────────────────────────────────────────────────── */
  const fetchMetrics = useCallback(async () => {
    try {
      const data = await adminService.getMetrics()
      setMetrics(data)
    } catch (err) {
      if (err.response?.status === 403) {
        setError('You do not have admin privileges.')
      } else {
        showErrorToast('Failed to load metrics')
      }
    }
  }, [])

  const fetchUsers = useCallback(async (page = 1, search = '') => {
    setLoading(true)
    try {
      const data = await adminService.getUsers(page, 20, search)
      setUsers(data.users)
      setUsersPagination({ total: data.total, page: data.page, pages: data.pages, per_page: data.per_page })
    } catch (err) {
      if (err.response?.status === 403) {
        setError('You do not have admin privileges.')
      } else {
        showErrorToast('Failed to load users')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchHealth = useCallback(async () => {
    try {
      const data = await adminService.getHealth()
      setHealth(data)
    } catch {
      showErrorToast('Failed to load health status')
    }
  }, [])

  const fetchAuditLog = useCallback(async () => {
    try {
      const data = await adminService.getAuditLog(50)
      setAuditLog(data)
    } catch {
      /* audit table may not exist yet */
      setAuditLog([])
    }
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      fetchMetrics()
      fetchUsers(1)
      fetchHealth()
      fetchAuditLog()
    }
  }, [isAuthenticated, fetchMetrics, fetchUsers, fetchHealth, fetchAuditLog])

  const handleSuspendToggle = async (userId, currentlyActive) => {
    try {
      const action = currentlyActive ? true : false
      await adminService.suspendUser(userId, action, currentlyActive ? 'Admin suspended' : '')
      showSuccessToast(currentlyActive ? 'User suspended' : 'User reactivated')
      fetchUsers(usersPagination.page, searchQuery)
    } catch {
      showErrorToast('Failed to update user status')
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    fetchUsers(1, searchQuery)
  }

  if (authLoading) {
    return <Layout><div className="flex items-center justify-center h-screen"><LoadingSpinner /></div></Layout>
  }
  if (!isAuthenticated) return null

  if (error) {
    return (
      <Layout>
        <PageContainer title="Admin Dashboard" subtitle="Access restricted">
          <Card className="p-8 text-center bg-white dark:bg-gray-800">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Access Denied</h3>
            <p className="text-gray-600 dark:text-gray-400">{error}</p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
              Admin access is granted to users listed in the <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">ADMIN_EMAILS</code> environment variable.
            </p>
          </Card>
        </PageContainer>
      </Layout>
    )
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'health', label: 'Health', icon: Server },
    { id: 'audit', label: 'Audit Log', icon: Shield },
  ]

  return (
    <Layout>
      <PageContainer title="Admin Dashboard" subtitle="Platform management and monitoring">
        {/* Tab Navigation */}
        <div className="flex gap-1 mb-6 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 overflow-x-auto">
          {tabs.map(({ id, label, icon: TabIcon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === id
                  ? 'bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              <TabIcon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* ── Overview Tab ──────────────────────────────────────────────── */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Platform Metrics</h2>
              <Button variant="secondary" onClick={fetchMetrics} className="flex items-center gap-2">
                <RefreshCw className="w-4 h-4" /> Refresh
              </Button>
            </div>

            {metrics ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard icon={Users} label="Total Users" value={metrics.total_users} color="blue" />
                <MetricCard icon={Activity} label="Active (24h)" value={metrics.active_users_24h} color="green" />
                <MetricCard icon={TrendingUp} label="Active (7d)" value={metrics.active_users_7d} color="purple" />
                <MetricCard icon={UserPlus} label="New Today" value={metrics.new_users_today} color="orange" />
                <MetricCard icon={BarChart3} label="Total Expenses" value={metrics.total_expenses} color="red" />
                <MetricCard icon={BarChart3} label="Total Budgets" value={metrics.total_budgets} color="indigo" />
                <MetricCard icon={BarChart3} label="Total Goals" value={metrics.total_goals} color="teal" />
              </div>
            ) : (
              <div className="flex justify-center py-12"><LoadingSpinner /></div>
            )}

            {/* Quick Health Summary */}
            {health && (
              <Card className="p-6 bg-white dark:bg-gray-800">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Infrastructure Status</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {Object.entries(health.checks || {}).map(([name, status]) => (
                    <div key={name} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
                      <div className={`w-3 h-3 rounded-full ${status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`} />
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">{name.replace('_', ' ')}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{status}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}

        {/* ── Users Tab ────────────────────────────────────────────────── */}
        {activeTab === 'users' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">User Management</h2>
              <form onSubmit={handleSearch} className="flex gap-2 w-full sm:w-auto">
                <div className="relative flex-1 sm:w-64">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search by email..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
                  />
                </div>
                <Button type="submit" variant="secondary">Search</Button>
              </form>
            </div>

            {/* Users Table */}
            <Card className="overflow-hidden bg-white dark:bg-gray-800">
              {loading ? (
                <div className="flex justify-center py-12"><LoadingSpinner /></div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-700/50">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Email</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Status</th>
                        <th className="hidden sm:table-cell px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">2FA</th>
                        <th className="hidden md:table-cell px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Last Login</th>
                        <th className="hidden md:table-cell px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Joined</th>
                        <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {users.map((user) => (
                        <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                          <td className="px-4 py-3 text-gray-900 dark:text-white font-medium">{user.email}</td>
                          <td className="px-4 py-3"><StatusBadge active={user.is_active} verified={user.is_verified} /></td>
                          <td className="hidden sm:table-cell px-4 py-3">
                            {user.totp_enabled ? (
                              <span className="text-green-600 dark:text-green-400 text-xs font-medium">Enabled</span>
                            ) : (
                              <span className="text-gray-400 dark:text-gray-500 text-xs">Off</span>
                            )}
                          </td>
                          <td className="hidden md:table-cell px-4 py-3 text-gray-600 dark:text-gray-400 text-xs">
                            {user.last_login ? new Date(user.last_login).toLocaleDateString() : '—'}
                          </td>
                          <td className="hidden md:table-cell px-4 py-3 text-gray-600 dark:text-gray-400 text-xs">
                            {user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => handleSuspendToggle(user.id, user.is_active)}
                              className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-colors ${
                                user.is_active
                                  ? 'bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/40'
                                  : 'bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/40'
                              }`}
                            >
                              {user.is_active ? <Ban className="w-3 h-3" /> : <CheckCircle className="w-3 h-3" />}
                              <span className="hidden sm:inline">{user.is_active ? ' Suspend' : ' Activate'}</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                      {users.length === 0 && (
                        <tr>
                          <td colSpan={6} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                            No users found.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination */}
              {usersPagination.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Showing page {usersPagination.page} of {usersPagination.pages} ({usersPagination.total} total)
                  </p>
                  <div className="flex gap-2">
                    <button
                      disabled={usersPagination.page <= 1}
                      onClick={() => fetchUsers(usersPagination.page - 1, searchQuery)}
                      className="p-2 rounded-md border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      disabled={usersPagination.page >= usersPagination.pages}
                      onClick={() => fetchUsers(usersPagination.page + 1, searchQuery)}
                      className="p-2 rounded-md border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* ── Health Tab ───────────────────────────────────────────────── */}
        {activeTab === 'health' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Infrastructure Health</h2>
              <Button variant="secondary" onClick={fetchHealth} className="flex items-center gap-2">
                <RefreshCw className="w-4 h-4" /> Refresh
              </Button>
            </div>

            {health ? (
              <Card className="p-6 bg-white dark:bg-gray-800">
                <div className="flex items-center gap-3 mb-6">
                  <div className={`w-4 h-4 rounded-full ${health.status === 'healthy' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                  <span className="text-lg font-semibold text-gray-900 dark:text-white capitalize">{health.status}</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Checked: {new Date(health.checked_at).toLocaleString()}
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(health.checks || {}).map(([name, status]) => (
                    <div
                      key={name}
                      className={`p-4 rounded-lg border ${
                        status === 'healthy'
                          ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20'
                          : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {status === 'healthy' ? (
                          <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />
                        )}
                        <span className="font-medium text-gray-900 dark:text-white capitalize">
                          {name.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{status}</p>
                    </div>
                  ))}
                </div>
              </Card>
            ) : (
              <div className="flex justify-center py-12"><LoadingSpinner /></div>
            )}
          </div>
        )}

        {/* ── Audit Log Tab ────────────────────────────────────────────── */}
        {activeTab === 'audit' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Audit Log</h2>
              <Button variant="secondary" onClick={fetchAuditLog} className="flex items-center gap-2">
                <RefreshCw className="w-4 h-4" /> Refresh
              </Button>
            </div>

            <Card className="overflow-hidden bg-white dark:bg-gray-800">
              {auditLog.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-700/50">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Table</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Record ID</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Deleted By</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Reason</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {auditLog.map((entry, i) => (
                        <tr key={entry.id || i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-4 py-3 text-gray-900 dark:text-white">{entry.table_name}</td>
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-400 text-xs font-mono">{entry.record_id}</td>
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{entry.deleted_by}</td>
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{entry.reason || '—'}</td>
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-400 text-xs">
                            {entry.created_at ? new Date(entry.created_at).toLocaleString() : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-12 text-center text-gray-500 dark:text-gray-400">
                  <Shield className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No audit log entries yet.</p>
                </div>
              )}
            </Card>
          </div>
        )}
      </PageContainer>
    </Layout>
  )
}
