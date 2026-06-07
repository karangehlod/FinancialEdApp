/**
 * Store Utilities for Redux-like state management patterns with Zustand
 * Provides common patterns, middleware, and utilities for state management
 */

/**
 * Create a reducer-like function for handling multiple actions
 * @param {Object} handlers - Object with action handlers
 * @returns {Function} Reducer function
 */
export const createReducer = (handlers) => {
  return (state, action) => {
    const handler = handlers[action.type]
    return handler ? handler(state, action.payload) : state
  }
}

/**
 * Async action wrapper with loading and error states
 * @param {Function} asyncFn - Async function to wrap
 * @returns {Function} Wrapped function
 */
export const createAsyncAction = (asyncFn) => {
  return async (set, get) => {
    return async (...args) => {
      set({ isLoading: true, error: null })
      try {
        const result = await asyncFn(...args)
        set({ isLoading: false })
        return result
      } catch (error) {
        const errorMessage = error.response?.data?.detail || error.message || 'An error occurred'
        set({ isLoading: false, error: errorMessage })
        throw error
      }
    }
  }
}

/**
 * Devtools middleware for debugging (optional)
 */
export const createWithDevtools = (name, initializer) => {
  return (set, get) => {
    const state = initializer(set, get)
    if (typeof window !== 'undefined' && window.__ZUSTAND_DEVTOOLS_AVAILABLE__) {
      return {
        ...state,
        __devtools: {
          name,
          enabled: true,
        },
      }
    }
    return state
  }
}

/**
 * Selector hook creator for memoized selectors
 * @param {Function} store - Zustand store hook
 * @param {Function} selector - Selector function
 * @returns {Function} Memoized selector
 */
export const createSelector = (store, selector) => {
  return () => {
    const state = store()
    return selector(state)
  }
}

/**
 * Store action logger middleware
 * @param {Object} store - Zustand store state
 * @param {string} actionName - Name of the action
 */
export const logAction = (store, actionName, payload = null) => {
  if (process.env.NODE_ENV === 'development') {
    // logger.info(`store:${store}`, { action: actionName, payload })
  }
}

/**
 * Reset store to initial state
 * @param {Function} set - Zustand set function
 * @param {Object} initialState - Initial state object
 */
export const createResetAction = (set, initialState) => {
  return () => {
    set(initialState)
  }
}

/**
 * Batch update multiple fields
 * @param {Function} set - Zustand set function
 * @param {Object} updates - Object with field updates
 */
export const batchUpdate = (set, updates) => {
  set((state) => ({ ...state, ...updates }))
}

/**
 * Create paginated query helper
 * @param {Function} fetchFn - Fetch function
 * @param {Function} set - Zustand set function
 */
export const createPaginationHelper = (fetchFn, set) => {
  return async (page = 1, limit = 10, filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetchFn({ page, limit, ...filters })
      set({
        data: response.data,
        pagination: {
          page: response.page,
          limit: response.limit,
          total: response.total,
          pages: response.pages,
        },
        isLoading: false,
      })
      return response
    } catch (error) {
      set({ isLoading: false, error: 'Failed to fetch data' })
      throw error
    }
  }
}

/**
 * Common state shape for CRUD operations
 */
export const CRUD_STATE_SHAPE = {
  data: [],
  currentItem: null,
  isLoading: false,
  error: null,
  pagination: {
    page: 1,
    limit: 10,
    total: 0,
    pages: 0,
  },
}

/**
 * Helper to create CRUD store actions
 * @param {Object} service - API service object with CRUD methods
 * @returns {Object} CRUD action functions
 */
export const createCRUDActions = (service) => ({
  // Fetch all items
  fetchAll: async (set, get) => {
    return async (filters = {}) => {
      set({ isLoading: true, error: null })
      try {
        const data = await service.getAll(filters)
        set({ data, isLoading: false })
        return data
      } catch (error) {
        set({ isLoading: false, error: 'Failed to fetch items' })
        throw error
      }
    }
  },

  // Fetch single item
  fetchOne: async (set, get) => {
    return async (id) => {
      set({ isLoading: true, error: null })
      try {
        const item = await service.getOne(id)
        set({ currentItem: item, isLoading: false })
        return item
      } catch (error) {
        set({ isLoading: false, error: 'Failed to fetch item' })
        throw error
      }
    }
  },

  // Create item
  create: async (set, get) => {
    return async (itemData) => {
      set({ isLoading: true, error: null })
      try {
        const newItem = await service.create(itemData)
        set((state) => ({
          data: [...state.data, newItem],
          isLoading: false,
        }))
        return newItem
      } catch (error) {
        set({ isLoading: false, error: 'Failed to create item' })
        throw error
      }
    }
  },

  // Update item
  update: async (set, get) => {
    return async (id, itemData) => {
      set({ isLoading: true, error: null })
      try {
        const updated = await service.update(id, itemData)
        set((state) => ({
          data: state.data.map((item) => (item.id === id ? updated : item)),
          currentItem: state.currentItem?.id === id ? updated : state.currentItem,
          isLoading: false,
        }))
        return updated
      } catch (error) {
        set({ isLoading: false, error: 'Failed to update item' })
        throw error
      }
    }
  },

  // Delete item
  delete: async (set, get) => {
    return async (id) => {
      set({ isLoading: true, error: null })
      try {
        await service.delete(id)
        set((state) => ({
          data: state.data.filter((item) => item.id !== id),
          currentItem: state.currentItem?.id === id ? null : state.currentItem,
          isLoading: false,
        }))
      } catch (error) {
        set({ isLoading: false, error: 'Failed to delete item' })
        throw error
      }
    }
  },

  // Clear error
  clearError: (set) => {
    set({ error: null })
  },

  // Reset store
  reset: (set) => {
    set({
      data: [],
      currentItem: null,
      isLoading: false,
      error: null,
    })
  },
})

/**
 * Persist middleware configuration
 */
export const persistConfig = {
  name: 'fined-storage', // unique name for localStorage key
  version: 1,
  migrate: (persistedState, version) => persistedState, // migration logic if needed
}
