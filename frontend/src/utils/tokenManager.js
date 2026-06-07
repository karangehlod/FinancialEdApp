/**
 * Token Manager - Handles token lifecycle and expiration
 * Ensures access tokens are valid for 1 hour before automatic refresh
 * Provides robust session persistence and recovery
 */

const TOKEN_EXPIRATION_TIME = 3600 * 1000 // 1 hour in milliseconds
const REFRESH_WARNING_TIME = 5 * 60 * 1000 // 5 minutes before expiration
const STORAGE_PREFIX = 'fin_ed_'
let tokenRefreshTimer = null
let tokenWarningTimer = null
let onTokenExpired = null
let onTokenWarning = null

/**
 * Get storage key with prefix to avoid conflicts
 */
const getStorageKey = (key) => `${STORAGE_PREFIX}${key}`

/**
 * Set callbacks for token events
 */
export const setTokenCallbacks = (onExpired, onWarning) => {
  onTokenExpired = onExpired
  onTokenWarning = onWarning
}

/**
 * Store token with expiration timestamp
 */
export const storeToken = (accessToken, refreshToken) => {
  if (!accessToken || !refreshToken) {
    console.error('Invalid tokens provided to storeToken')
    return false
  }
  
  try {
    const expirationTime = Date.now() + TOKEN_EXPIRATION_TIME
    
    localStorage.setItem(getStorageKey('access_token'), accessToken)
    localStorage.setItem(getStorageKey('refresh_token'), refreshToken)
    localStorage.setItem(getStorageKey('token_expiration'), expirationTime.toString())
    localStorage.setItem(getStorageKey('token_issued_at'), Date.now().toString())
    localStorage.setItem(getStorageKey('session_valid'), 'true')
    
    // Schedule token refresh
    scheduleTokenRefresh()
    return true
  } catch (error) {
    console.error('Failed to store token:', error)
    return false
  }
}

/**
 * Get remaining token validity time in milliseconds
 */
export const getTokenTimeRemaining = () => {
  try {
    const expirationTime = parseInt(localStorage.getItem(getStorageKey('token_expiration')), 10)
    if (!expirationTime || isNaN(expirationTime)) return 0
    
    const remaining = expirationTime - Date.now()
    return Math.max(0, remaining)
  } catch (error) {
    console.error('Error calculating token time remaining:', error)
    return 0
  }
}

/**
 * Check if token is valid (not expired)
 */
export const isTokenValid = () => {
  try {
    const expirationTime = parseInt(localStorage.getItem(getStorageKey('token_expiration')), 10)
    if (!expirationTime || isNaN(expirationTime)) return false
    
    const isValid = Date.now() < expirationTime
    
    // Update session validity marker
    if (isValid) {
      localStorage.setItem(getStorageKey('session_valid'), 'true')
    } else {
      localStorage.setItem(getStorageKey('session_valid'), 'false')
    }
    
    return isValid
  } catch (error) {
    console.error('Error checking token validity:', error)
    return false
  }
}

/**
 * Check if token should be refreshed (approaching expiration)
 */
export const shouldRefreshToken = () => {
  try {
    const timeRemaining = getTokenTimeRemaining()
    return timeRemaining < REFRESH_WARNING_TIME && timeRemaining > 0
  } catch (error) {
    console.error('Error checking if token should be refreshed:', error)
    return false
  }
}

/**
 * Get token expiration time as Date object
 */
export const getTokenExpirationTime = () => {
  try {
    const expirationTime = parseInt(localStorage.getItem(getStorageKey('token_expiration')), 10)
    if (!expirationTime || isNaN(expirationTime)) return null
    
    return new Date(expirationTime)
  } catch (error) {
    console.error('Error getting token expiration time:', error)
    return null
  }
}

/**
 * Format remaining time for display
 */
export const formatTokenTimeRemaining = () => {
  const remaining = getTokenTimeRemaining()
  
  if (remaining <= 0) return 'Expired'
  
  const minutes = Math.floor(remaining / 60000)
  const seconds = Math.floor((remaining % 60000) / 1000)
  
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  }
  return `${seconds}s`
}

/**
 * Schedule token refresh
 */
export const scheduleTokenRefresh = () => {
  // Clear existing timers
  clearTokenTimers()
  
  try {
    const timeRemaining = getTokenTimeRemaining()
    
    if (timeRemaining <= 0) {
      // Token already expired
      if (onTokenExpired) {
        onTokenExpired()
      }
      return
    }
    
    // Set warning timer (5 minutes before expiration)
    const warningTime = Math.max(0, timeRemaining - REFRESH_WARNING_TIME)
    if (warningTime > 0) {
      tokenWarningTimer = setTimeout(() => {
        if (onTokenWarning) {
          onTokenWarning()
        }
      }, warningTime)
    }
    
    // Set expiration timer
    tokenRefreshTimer = setTimeout(() => {
      if (onTokenExpired) {
        onTokenExpired()
      }
    }, timeRemaining)
  } catch (error) {
    console.error('Error scheduling token refresh:', error)
  }
}

/**
 * Clear token timers
 */
export const clearTokenTimers = () => {
  if (tokenRefreshTimer) {
    clearTimeout(tokenRefreshTimer)
    tokenRefreshTimer = null
  }
  if (tokenWarningTimer) {
    clearTimeout(tokenWarningTimer)
    tokenWarningTimer = null
  }
}

/**
 * Clear all token data and session
 */
export const clearTokens = () => {
  try {
    localStorage.removeItem(getStorageKey('access_token'))
    localStorage.removeItem(getStorageKey('refresh_token'))
    localStorage.removeItem(getStorageKey('token_expiration'))
    localStorage.removeItem(getStorageKey('token_issued_at'))
    localStorage.removeItem(getStorageKey('session_valid'))
    clearTokenTimers()
  } catch (error) {
    console.error('Error clearing tokens:', error)
  }
}

/**
 * Get current access token
 */
export const getAccessToken = () => {
  try {
    return localStorage.getItem(getStorageKey('access_token'))
  } catch (error) {
    console.error('Error getting access token:', error)
    return null
  }
}

/**
 * Get current refresh token
 */
export const getRefreshToken = () => {
  try {
    return localStorage.getItem(getStorageKey('refresh_token'))
  } catch (error) {
    console.error('Error getting refresh token:', error)
    return null
  }
}

/**
 * Update token expiration without changing the token itself
 * (Used after successful refresh)
 */
export const updateTokenExpiration = () => {
  try {
    const expirationTime = Date.now() + TOKEN_EXPIRATION_TIME
    localStorage.setItem(getStorageKey('token_expiration'), expirationTime.toString())
    localStorage.setItem(getStorageKey('session_valid'), 'true')
    scheduleTokenRefresh()
  } catch (error) {
    console.error('Error updating token expiration:', error)
  }
}

/**
 * Get token status for debugging and monitoring
 */
export const getTokenStatus = () => {
  try {
    return {
      hasAccessToken: !!getAccessToken(),
      hasRefreshToken: !!getRefreshToken(),
      isValid: isTokenValid(),
      timeRemaining: formatTokenTimeRemaining(),
      expiresAt: getTokenExpirationTime(),
      shouldRefresh: shouldRefreshToken(),
      sessionValid: localStorage.getItem(getStorageKey('session_valid')) === 'true',
    }
  } catch (error) {
    console.error('Error getting token status:', error)
    return {
      hasAccessToken: false,
      hasRefreshToken: false,
      isValid: false,
      timeRemaining: 'Error',
      expiresAt: null,
      shouldRefresh: false,
      sessionValid: false,
    }
  }
}


export default {
  storeToken,
  getTokenTimeRemaining,
  isTokenValid,
  shouldRefreshToken,
  getTokenExpirationTime,
  formatTokenTimeRemaining,
  scheduleTokenRefresh,
  clearTokenTimers,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  updateTokenExpiration,
  getTokenStatus,
  setTokenCallbacks,
}
