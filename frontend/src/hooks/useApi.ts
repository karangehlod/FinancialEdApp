/**
 * useApi Hook - Simplified API calls with automatic retry and error handling
 * 
 * Features:
 * - Automatic retry with exponential backoff
 * - Error notification through toast system
 * - Loading and error states
 * - Abort signal support for cleanup
 */

import { useCallback, useState, useRef, useEffect } from 'react'
import { enhancedApiService } from '@/services/enhancedApiService'
import { notificationManager } from '@/utils/errorNotificationManager'
import logger from '@/utils/logger'

export interface UseApiState<T> {
  data: T | null
  isLoading: boolean
  error: unknown | null
  retry: () => Promise<void>
}

export interface UseApiOptions {
  maxRetries?: number
  autoFetch?: boolean
  showErrorNotification?: boolean
  errorContext?: { code: string; context?: Record<string, unknown> }
}

/**
 * Hook for API GET requests
 */
export function useApiGet<T = unknown>(
  url: string,
  options?: UseApiOptions
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<unknown | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const fetchData = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setIsLoading(true)
        setError(null)

        const response = await enhancedApiService.get<T>(url, {
          maxRetries: options?.maxRetries,
          onRetry: (attemptNumber, delayMs) => {
            logger.debug('Retrying API request', { url, attemptNumber, delayMs })
          },
        })

        if (!signal?.aborted) {
          setData(response)
        }
      } catch (err) {
        if (!signal?.aborted) {
          setError(err)

          if (options?.showErrorNotification !== false) {
            notificationManager.showError(err, options?.errorContext)
          }

          logger.error('API request failed', {
            url,
            error: err instanceof Error ? err.message : String(err),
          })
        }
      } finally {
        if (!signal?.aborted) {
          setIsLoading(false)
        }
      }
    },
    [url, options]
  )

  useEffect(() => {
    if (options?.autoFetch === false) {
      return
    }

    const controller = new AbortController()
    abortControllerRef.current = controller

    fetchData(controller.signal)

    return () => {
      controller.abort()
    }
  }, [fetchData, options?.autoFetch])

  const retry = useCallback(async () => {
    await fetchData()
  }, [fetchData])

  return { data, isLoading, error, retry }
}

/**
 * Hook for API mutations (POST, PUT, PATCH, DELETE)
 */
export function useApiMutation<TRequest = unknown, TResponse = unknown>(
  method: 'post' | 'put' | 'patch' | 'delete' = 'post'
) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<unknown | null>(null)

  const mutate = useCallback(
    async (
      url: string,
      data?: TRequest,
      options?: UseApiOptions & {
        onSuccess?: (response: TResponse) => void
      }
    ): Promise<TResponse | null> => {
      try {
        setIsLoading(true)
        setError(null)

        let response: TResponse

        switch (method) {
          case 'post':
            response = await enhancedApiService.post<TResponse>(url, data, {
              maxRetries: options?.maxRetries,
            })
            break
          case 'put':
            response = await enhancedApiService.put<TResponse>(url, data, {
              maxRetries: options?.maxRetries,
            })
            break
          case 'patch':
            response = await enhancedApiService.patch<TResponse>(url, data, {
              maxRetries: options?.maxRetries,
            })
            break
          case 'delete':
            response = await enhancedApiService.delete<TResponse>(url, {
              maxRetries: options?.maxRetries,
            })
            break
          default:
            throw new Error(`Unsupported method: ${method}`)
        }

        setError(null)
        options?.onSuccess?.(response)

        return response
      } catch (err) {
        setError(err)

        if (options?.showErrorNotification !== false) {
          notificationManager.showError(err, {
            code: options?.errorContext?.code || method.toUpperCase(),
            context: options?.errorContext?.context,
          })
        }

        logger.error('Mutation failed', {
          method,
          url,
          error: err instanceof Error ? err.message : String(err),
        })

        return null
      } finally {
        setIsLoading(false)
      }
    },
    [method]
  )

  const reset = useCallback(() => {
    setIsLoading(false)
    setError(null)
  }, [])

  return { mutate, isLoading, error, reset }
}

/**
 * Hook for checking network status and queued requests
 */
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' && navigator.onLine
  )
  const [queueSize, setQueueSize] = useState(0)

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      logger.info('Application is online')
    }

    const handleOffline = () => {
      setIsOnline(false)
      logger.info('Application is offline')
    }

    const handleNetworkOnline = () => {
      setIsOnline(true)
      setQueueSize(enhancedApiService.getOfflineQueueStatus().queueSize)
    }

    const handleNetworkOffline = () => {
      setIsOnline(false)
      setQueueSize(enhancedApiService.getOfflineQueueStatus().queueSize)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    window.addEventListener('network-online', handleNetworkOnline)
    window.addEventListener('network-offline', handleNetworkOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('network-online', handleNetworkOnline)
      window.removeEventListener('network-offline', handleNetworkOffline)
    }
  }, [])

  const processQueue = useCallback(async () => {
    const result = await enhancedApiService.processQueuedRequests((completed, total) => {
      logger.debug('Processing queue', { completed, total })
    })

    setQueueSize(enhancedApiService.getOfflineQueueStatus().queueSize)
    return result
  }, [])

  return { isOnline, queueSize, processQueue }
}

/**
 * Hook for pagination with API
 */
export function useApiPagination<T = unknown>(
  url: string,
  pageSize: number = 10,
  options?: UseApiOptions
) {
  const [page, setPage] = useState(1)
  const [data, setData] = useState<T[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<unknown | null>(null)

  const fetchPage = useCallback(
    async (pageNum: number) => {
      try {
        setIsLoading(true)
        setError(null)

        const skip = (pageNum - 1) * pageSize
        const paginatedUrl = `${url}?skip=${skip}&limit=${pageSize}`

        const response = await enhancedApiService.get<{
          data: T[]
          total: number
        }>(paginatedUrl, {
          maxRetries: options?.maxRetries,
        })

        setData(response.data)
        setTotalCount(response.total)
        setPage(pageNum)
      } catch (err) {
        setError(err)

        if (options?.showErrorNotification !== false) {
          notificationManager.showError(err, options?.errorContext)
        }
      } finally {
        setIsLoading(false)
      }
    },
    [url, pageSize, options]
  )

  useEffect(() => {
    fetchPage(1)
  }, [fetchPage])

  const totalPages = Math.ceil(totalCount / pageSize)

  return {
    data,
    page,
    totalPages,
    totalCount,
    isLoading,
    error,
    goToPage: fetchPage,
    nextPage: () => page < totalPages && fetchPage(page + 1),
    prevPage: () => page > 1 && fetchPage(page - 1),
  }
}
