/**
 * Format currency values
 */
export const formatCurrency = (value, currency = 'USD') => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(value)
}

/**
 * Format percentage with decimal places
 */
export const formatPercentage = (value, decimals = 1) => {
  return `${(value * 100).toFixed(decimals)}%`
}

/**
 * Format date
 */
export const formatDate = (date, format = 'MMM dd, yyyy') => {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  }).format(new Date(date))
}

/**
 * Format large numbers (e.g., 1000 -> 1K)
 */
export const formatNumber = (num) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toFixed(2)
}

/**
 * Get category color
 */
export const getCategoryColor = (category) => {
  const colors = {
    food: 'bg-red-100 text-red-800',
    transport: 'bg-blue-100 text-blue-800',
    utilities: 'bg-yellow-100 text-yellow-800',
    entertainment: 'bg-purple-100 text-purple-800',
    health: 'bg-green-100 text-green-800',
    education: 'bg-indigo-100 text-indigo-800',
    shopping: 'bg-pink-100 text-pink-800',
    other: 'bg-gray-100 text-gray-800',
  }
  return colors[category?.toLowerCase()] || colors.other
}

/**
 * Get status color
 */
export const getStatusColor = (status) => {
  const colors = {
    active: 'bg-green-100 text-green-800',
    inactive: 'bg-gray-100 text-gray-800',
    pending: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-blue-100 text-blue-800',
    failed: 'bg-red-100 text-red-800',
  }
  return colors[status?.toLowerCase()] || colors.inactive
}

/**
 * Calculate percentage
 */
export const calculatePercentage = (current, total) => {
  return total === 0 ? 0 : (current / total) * 100
}

/**
 * Download file from blob
 */
export const downloadFile = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Validate email
 */
export const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(email)
}

/**
 * Get initials from name
 */
export const getInitials = (name) => {
  if (!name || typeof name !== 'string') {
    return 'U'
  }
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
}
