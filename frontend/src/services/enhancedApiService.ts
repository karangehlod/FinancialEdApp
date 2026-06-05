/**
 * Enhanced API Service with Network Retry Manager Integration
 * 
 * Features:
 * - Automatic retry on network failures and specific status codes
 * - Offline detection and request queuing
 * - Request deduplication
 * - Event-based retry notifications
 */

import apiClient from './api'
import { networkRetryManager } from './networkRetryManager'
import logger from '@/utils/logger'

export interface ApiRequestOptions {
  maxRetries?: number
  timeout?: number
  onRetry?: (attemptNumber: number, delayMs: number) => void
  onError?: (error: unknown) => void
  bypassRetry?: boolean
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

/**
 * Enhanced API Service with retry capabilities
 */
export class EnhancedApiService {
  private requestDeduplicator = new Map<string, Promise<unknown>>()

  /**
   * GET request with automatic retry
   */
  async get<T = unknown>(
    url: string,
    options?: ApiRequestOptions
  ): Promise<T> {
    return this.executeWithRetry(() => apiClient.get<T>(url), url, 'GET', options)
  }

  /**
   * POST request with automatic retry
   */
  async post<T = unknown>(
    url: string,
    data?: unknown,
    options?: ApiRequestOptions
  ): Promise<T> {
    return this.executeWithRetry(() => apiClient.post<T>(url, data), url, 'POST', options, data)
  }

  /**
   * PUT request with automatic retry
   */
  async put<T = unknown>(
    url: string,
    data?: unknown,
    options?: ApiRequestOptions
  ): Promise<T> {
    return this.executeWithRetry(() => apiClient.put<T>(url, data), url, 'PUT', options, data)
  }

  /**
   * PATCH request with automatic retry
   */
  async patch<T = unknown>(
    url: string,
    patchData?: unknown,
    options?: ApiRequestOptions
  ): Promise<T> {
    return this.executeWithRetry(
      () => apiClient.patch<T>(url, patchData),
      url,
      'PATCH',
      options,
      patchData
    )
  }

  /**
   * DELETE request with automatic retry
   */
  async delete<T = unknown>(
    url: string,
    options?: ApiRequestOptions
  ): Promise<T> {
    return this.executeWithRetry(() => apiClient.delete<T>(url), url, 'DELETE', options)
  }

  /**
   * Internal retry execution handler
   */
  private async executeWithRetry<T>(
    requestFn: () => Promise<{ data: T }>,
    url: string,
    method: string,
    options?: ApiRequestOptions,
    data?: unknown
  ): Promise<T> {
    const deduplicationKey = `${method}:${url}`

    // Check if request is already in progress (deduplication)
    if (this.requestDeduplicator.has(deduplicationKey)) {
      logger.debug('Request deduplicated', { url, method })
      return (await this.requestDeduplicator.get(deduplicationKey)) as Promise<T>
    }

    if (options?.bypassRetry) {
      try {
        const response = await requestFn()
        return response.data
      } catch (error) {
        options?.onError?.(error)
        throw error
      }
    }

    // Create the actual request promise
    const requestPromise = (async () => {
      try {
        const response = await networkRetryManager.executeWithRetry(requestFn, {
          maxAttempts: options?.maxRetries,
          onRetry: (attemptNumber, delayMs) => {
            logger.warn('Retrying request', { url, method, attemptNumber, delayMs })
            options?.onRetry?.(attemptNumber, delayMs)
            // Dispatch retry event for UI
            window.dispatchEvent(
              new CustomEvent('api-retry', {
                detail: { url, method, attemptNumber, delayMs },
              })
            )
          },
          onFailed: (error) => {
            logger.error('Request failed after retries', {
              url,
              method,
              error: error instanceof Error ? error.message : String(error),
            })
            options?.onError?.(error)
          },
        })

        return response.data
      } finally {
        // Remove from deduplicator after completion
        this.requestDeduplicator.delete(deduplicationKey)
      }
    })()

    // Store in deduplicator
    this.requestDeduplicator.set(deduplicationKey, requestPromise)

    return (await requestPromise) as T
  }

  /**
   * Queue a request for offline retry
   */
  queueRequestForOfflineRetry(
    method: string,
    url: string,
    data?: Record<string, unknown>,
    priority?: 'high' | 'normal' | 'low'
  ): string {
    const requestId = networkRetryManager.queueRequest(method, url, data, undefined, priority)
    logger.info('Request queued for offline retry', { url, method, requestId })
    return requestId
  }

  /**
   * Get offline request queue status
   */
  getOfflineQueueStatus(): {
    isOnline: boolean
    queueSize: number
    queuedRequests: Array<{
      id: string
      method: string
      url: string
      priority: string
      timestamp: number
    }>
  } {
    const queuedRequests = networkRetryManager.getQueuedRequests().map((req) => ({
      id: req.id,
      method: req.method,
      url: req.url,
      priority: req.priority,
      timestamp: req.timestamp,
    }))

    return {
      isOnline: networkRetryManager.getOnlineStatus(),
      queueSize: networkRetryManager.getQueueSize(),
      queuedRequests,
    }
  }

  /**
   * Retry a specific queued request
   */
  async retryQueuedRequest(
    requestId: string,
    onSuccess?: (result: unknown) => void,
    onError?: (error: unknown) => void
  ): Promise<void> {
    const request = networkRetryManager.dequeueRequest(requestId)
    if (!request) {
      logger.warn('Queued request not found', { requestId })
      return
    }

    try {
      request.attempts++
      const response = await networkRetryManager.executeWithRetry(
        () => apiClient({ method: request.method as any, url: request.url, data: request.data }),
        {
          onRetry: (attemptNumber, delayMs) => {
            logger.warn('Retrying queued request', { requestId, attemptNumber, delayMs })
          },
        }
      )

      networkRetryManager.removeRequest(request.id)
      onSuccess?.(response?.data)
      logger.info('Queued request succeeded', { requestId })
    } catch (error) {
      onError?.(error)
      logger.error('Queued request failed', {
        requestId,
        error: error instanceof Error ? error.message : String(error),
      })
    }
  }

  /**
   * Process all queued requests (call when coming back online)
   */
  async processQueuedRequests(
    onProgress?: (completed: number, total: number) => void
  ): Promise<{ successful: number; failed: number }> {
    if (!networkRetryManager.getOnlineStatus()) {
      logger.warn('Cannot process queue - still offline')
      return { successful: 0, failed: 0 }
    }

    const queuedRequests = networkRetryManager.getQueuedRequests()
    let successful = 0
    let failed = 0

    logger.info('Processing queued requests', { count: queuedRequests.length })

    for (let i = 0; i < queuedRequests.length; i++) {
      const request = queuedRequests[i]

      await this.retryQueuedRequest(
        request.id,
        () => {
          successful++
          onProgress?.(i + 1, queuedRequests.length)
        },
        () => {
          failed++
          onProgress?.(i + 1, queuedRequests.length)
        }
      )
    }

    logger.info('Queue processing complete', { successful, failed })
    return { successful, failed }
  }

  /**
   * Clear all queued requests
   */
  clearQueue(): void {
    networkRetryManager.clearQueue()
    logger.info('Offline request queue cleared')
  }
}

// Export singleton instance
export const enhancedApiService = new EnhancedApiService()

// Export for convenience
export default enhancedApiService
