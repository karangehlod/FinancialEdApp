/**
 * Pure utility functions — no side effects, fully typed.
 */

import type { ExpenseCategory, GoalStatus } from '@/types'

// ── Formatting ─────────────────────────────────────────────────────────

export function formatCurrency(value: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(value)
}

export function formatPercentage(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  }).format(new Date(date))
}

export function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`
  return num.toFixed(2)
}

// ── Validation ─────────────────────────────────────────────────────────

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function validateEmail(email: string): boolean {
  return EMAIL_REGEX.test(email)
}

export function sanitizeInput(input: string): string {
  const div = document.createElement('div')
  div.textContent = input
  return div.innerHTML
}

// ── UI Helpers ─────────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<ExpenseCategory, string> = {
  food: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  transport: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  utilities: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  entertainment: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
  health: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  education: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
  shopping: 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300',
  other: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300',
}

export function getCategoryColor(category: string): string {
  const key = category?.toLowerCase() as ExpenseCategory
  return CATEGORY_COLORS[key] ?? CATEGORY_COLORS.other
}

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  inactive: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300',
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  completed: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  paused: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300',
  paid_off: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  defaulted: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
}

export function getStatusColor(status: string | GoalStatus): string {
  return STATUS_COLORS[status?.toLowerCase()] ?? STATUS_COLORS['inactive']!
}

export function calculatePercentage(current: number, total: number): number {
  return total === 0 ? 0 : (current / total) * 100
}

export function getInitials(name: string | null | undefined): string {
  if (!name || typeof name !== 'string') return 'U'
  return name
    .split(' ')
    .map((n) => n[0])
    .filter(Boolean)
    .join('')
    .toUpperCase()
}

// ── File Utilities ─────────────────────────────────────────────────────

export function downloadFile(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// ── Class Name Merging ─────────────────────────────────────────────────

export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}
