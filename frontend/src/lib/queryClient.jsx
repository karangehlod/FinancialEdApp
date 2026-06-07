/**
 * React Query (TanStack Query) configuration.
 *
 * Provides:
 *   - Global QueryClient with production-tuned defaults
 *   - Stale time: 2 minutes (data stays fresh before re-fetching)
 *   - Retry: 2 retries with exponential backoff (skip 401/403 errors)
 *   - Cache time: 5 minutes (keeps unused data in memory)
 *   - Request deduplication: automatic (built into React Query)
 *   - Window focus refetch: enabled (re-validates on tab focus)
 *
 * Usage:
 *   Wrap your app with <QueryProvider> (already done in App.jsx/main.jsx).
 *   Use useQuery / useMutation hooks in components.
 *
 * Benefits over raw fetch/axios:
 *   - Automatic deduplication of identical concurrent requests
 *   - Background re-fetching for stale data
 *   - Optimistic updates support
 *   - Built-in loading / error / success states
 *   - Offline support (request queuing)
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ---------------------------------------------------------------------------
// Query Client — application-level singleton
// ---------------------------------------------------------------------------
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 2 minutes — no background refetch during this window
      staleTime: 2 * 60 * 1000,
      // Unused cache data is garbage-collected after 5 minutes
      gcTime: 5 * 60 * 1000,
      // Retry failed requests up to 2 times with exponential backoff
      retry: (failureCount, error) => {
        // Never retry on auth errors (401/403) or not-found (404)
        const status = error?.response?.status;
        if (status === 401 || status === 403 || status === 404) return false;
        return failureCount < 2;
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
      // Re-fetch on window focus (user returns to tab)
      refetchOnWindowFocus: true,
      // Re-fetch when network reconnects
      refetchOnReconnect: true,
      // Don't refetch on mount if data is still fresh
      refetchOnMount: true,
    },
    mutations: {
      // Retry mutations once on network error
      retry: (failureCount, error) => {
        const status = error?.response?.status;
        // Never retry on client errors
        if (status >= 400 && status < 500) return false;
        return failureCount < 1;
      },
    },
  },
});

// ---------------------------------------------------------------------------
// Query key factories — centralise cache key definitions
// Prevents typos and enables targeted cache invalidation.
// ---------------------------------------------------------------------------
export const queryKeys = {
  // Auth
  user: () => ['user', 'profile'],

  // Expenses
  expenses: {
    all: () => ['expenses'],
    list: (params) => ['expenses', 'list', params],
    detail: (id) => ['expenses', 'detail', id],
    analytics: (params) => ['expenses', 'analytics', params],
  },

  // Budgets
  budgets: {
    all: () => ['budgets'],
    list: () => ['budgets', 'list'],
    detail: (id) => ['budgets', 'detail', id],
    summary: () => ['budgets', 'summary'],
  },

  // Goals
  goals: {
    all: () => ['goals'],
    list: () => ['goals', 'list'],
    detail: (id) => ['goals', 'detail', id],
  },

  // Loans
  loans: {
    all: () => ['loans'],
    list: () => ['loans', 'list'],
    detail: (id) => ['loans', 'detail', id],
  },

  // Notifications
  notifications: {
    all: () => ['notifications'],
    unread: () => ['notifications', 'unread'],
  },
};

// ---------------------------------------------------------------------------
// Cache invalidation helpers — call after mutations to refresh relevant data
// ---------------------------------------------------------------------------
export const invalidateExpenses = () => {
  queryClient.invalidateQueries({ queryKey: queryKeys.expenses.all() });
  queryClient.invalidateQueries({ queryKey: queryKeys.budgets.all() }); // budgets depend on expenses
};

export const invalidateBudgets = () => {
  queryClient.invalidateQueries({ queryKey: queryKeys.budgets.all() });
};

export const invalidateGoals = () => {
  queryClient.invalidateQueries({ queryKey: queryKeys.goals.all() });
};

export const invalidateNotifications = () => {
  queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all() });
};

// ---------------------------------------------------------------------------
// Provider component
// ---------------------------------------------------------------------------
export function QueryProvider({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
