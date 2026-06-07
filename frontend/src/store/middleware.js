/**
 * Store Middleware and Enhancers
 * Provides enhanced functionality for Zustand stores
 */

/**
 * Devtools enhancer for debugging stores
 * @param {Function} createState - Zustand create state function
 * @param {string} name - Store name
 */
export const withDevtools = (createState, name) => {
  if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
    return createState
  }
  return createState
}

/**
 * Logger middleware for store actions
 * @param {Function} set - Zustand set function
 * @param {string} storeName - Name of the store
 */
export const createLoggerMiddleware = (set, storeName = 'Store') => {
  return (callback) => {
    return set((state) => {
      console.group(`[${storeName}] State Update`)
      // logger.debug('Previous state', { state })
      const updates = callback(state)
      // logger.debug('Updates', { updates })
      console.groupEnd()
      return updates
    })
  }
}

/**
 * Error handler middleware
 * @param {Function} set - Zustand set function
 */
export const createErrorHandlerMiddleware = (set) => {
  return (callback) => {
    return set((state) => {
      try {
        return callback(state)
      } catch (error) {
        console.error('Error in store action:', error)
        return state
      }
    })
  }
}

/**
 * Validation middleware to validate state changes
 * @param {Function} set - Zustand set function
 * @param {Object} schema - Validation schema
 */
export const createValidationMiddleware = (set, schema) => {
  return (callback) => {
    return set((state) => {
      const updates = callback(state)
      // Implement validation logic here if needed
      return updates
    })
  }
}

/**
 * Optimistic update middleware
 * Applies changes optimistically and reverts on error
 * @param {Function} set - Zustand set function
 */
export const createOptimisticMiddleware = (set) => {
  const originalSet = set
  let previousState = null

  return (callback) => {
    return originalSet((state) => {
      previousState = state
      try {
        return callback(state)
      } catch (error) {
        // Revert to previous state on error
        return previousState
      }
    })
  }
}

/**
 * Time-travel debugging middleware (for development)
 * Keeps history of state changes for debugging
 */
export const createTimeTravelMiddleware = () => {
  let history = []
  let currentIndex = -1

  return {
    recordState: (state) => {
      currentIndex++
      history = history.slice(0, currentIndex)
      history.push(JSON.parse(JSON.stringify(state)))
    },

    undo: () => {
      if (currentIndex > 0) {
        currentIndex--
        return history[currentIndex]
      }
      return null
    },

    redo: () => {
      if (currentIndex < history.length - 1) {
        currentIndex++
        return history[currentIndex]
      }
      return null
    },

    getHistory: () => history,
    getCurrentIndex: () => currentIndex,
  }
}

/**
 * Subscription middleware to listen to specific state changes
 * @param {Function} store - Zustand store hook
 * @param {Function} selector - Selector function
 * @param {Function} listener - Callback when state changes
 */
export const subscribeToStore = (store, selector, listener) => {
  let previousValue = selector(store.getState?.())

  const unsubscribe = store.subscribe((state) => {
    const currentValue = selector(state)
    if (previousValue !== currentValue) {
      listener(currentValue, previousValue)
      previousValue = currentValue
    }
  })

  return unsubscribe
}

/**
 * Batched updates helper
 * Groups multiple updates into a single state change
 * @param {Function} set - Zustand set function
 * @param {Array} updates - Array of update functions
 */
export const batchUpdates = (set, updates) => {
  set((state) => {
    let newState = state
    updates.forEach((update) => {
      newState = update(newState)
    })
    return newState
  })
}

/**
 * Create action thunk helper for async operations
 * Similar to Redux thunk
 * @param {Function} asyncAction - Async function
 * @param {Function} set - Zustand set function
 * @param {Function} get - Zustand get function
 */
export const createAsyncThunk = (asyncAction, set, get) => {
  return async (...args) => {
    set({ isLoading: true, error: null })
    try {
      const result = await asyncAction(...args)
      set({ isLoading: false })
      return result
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'An error occurred'
      set({ isLoading: false, error: errorMessage })
      throw error
    }
  }
}

/**
 * State selector with memoization
 * Helps prevent unnecessary re-renders
 * @param {Function} store - Zustand store
 * @param {Function} selector - Selector function
 */
export const useMemoSelector = (store, selector) => {
  let previousValue
  let previousState

  return () => {
    const state = store()
    // Only recompute if state reference changed
    if (previousState !== state) {
      previousValue = selector(state)
      previousState = state
    }
    return previousValue
  }
}

/**
 * Combine multiple stores into single hook
 * @param {...Function} stores - Zustand store hooks
 */
export const combineStores = (...stores) => {
  return () => {
    const combined = {}
    stores.forEach((store, index) => {
      combined[`store${index}`] = store()
    })
    return combined
  }
}

/**
 * Create derived state (computed properties)
 * @param {Function} store - Zustand store
 * @param {Function} deriveFn - Function to derive new state
 */
export const createDerivedState = (store, deriveFn) => {
  return () => {
    const state = store()
    return deriveFn(state)
  }
}

/**
 * Sync store with localStorage
 * @param {Function} set - Zustand set function
 * @param {Function} get - Zustand get function
 * @param {string} key - LocalStorage key
 * @param {Array} fieldsToSync - Array of field names to sync
 */
export const createLocalStorageSync = (set, get, key, fieldsToSync = []) => {
  // Load from localStorage on init
  const stored = localStorage.getItem(key)
  if (stored) {
    try {
      const data = JSON.parse(stored)
      set(data)
    } catch (error) {
      console.error('Failed to load from localStorage:', error)
    }
  }

  // Save to localStorage on changes
  return (state) => {
    const toSync = fieldsToSync.length > 0
      ? fieldsToSync.reduce((acc, field) => ({ ...acc, [field]: state[field] }), {})
      : state

    localStorage.setItem(key, JSON.stringify(toSync))
  }
}

/**
 * Create immer-compatible state updater (for immutable updates)
 * @param {Function} set - Zustand set function
 */
export const createImmerUpdater = (set) => {
  return (updateFn) => {
    set((state) => {
      const draft = JSON.parse(JSON.stringify(state))
      updateFn(draft)
      return draft
    })
  }
}
