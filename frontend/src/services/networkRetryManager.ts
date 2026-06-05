/**
 * Network Retry Manager - Handles exponential backoff and retry logic
 * 
 * Features:
 * - Exponential backoff with jitter
 * - Retry on specific status codes (429, 500, 502, 503, 504)
 * - Network error detection and recovery
 * - Request queue for offline scenarios
 */

export interface RetryConfig {
  maxAttempts: number
  initialDelayMs: number
  maxDelayMs: number
  backoffMultiplier: number
  jitterFactor: number
  retryableStatusCodes: number[]
}

export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  initialDelayMs: 1000,
  maxDelayMs: 10000,
  backoffMultiplier: 2,
  jitterFactor: 0.1, // 10% jitter
  retryableStatusCodes: [429, 500, 502, 503, 504],
}

export interface RetryableRequest {
  id: string
  timestamp: number
  method: string
  url: string
  data?: Record<string, unknown>
  headers?: Record<string, string>
  priority: 'high' | 'normal' | 'low'
  attempts: number
  nextRetryAt?: number
}

/**
 * Exponential backoff calculator with jitter
 */
export class BackoffCalculator {
  constructor(private config: RetryConfig = DEFAULT_RETRY_CONFIG) {}

  /**
   * Calculate delay for next retry attempt
   */
  calculateDelay(attemptNumber: number): number {
    const exponentialDelay = Math.min(
      this.config.initialDelayMs * Math.pow(this.config.backoffMultiplier, attemptNumber - 1),
      this.config.maxDelayMs
    )

    // Add jitter to prevent thundering herd
    const jitter = exponentialDelay * this.config.jitterFactor * Math.random()
    return exponentialDelay + jitter
  }

  /**
   * Check if error is retryable
   */
  isRetryable(error: unknown): boolean {
    if (error instanceof TypeError) {
      // Network errors (e.g., "Failed to fetch")
      return error.message.includes('fetch') || error.message.includes('Network')
    }

    if (typeof error === 'object' && error !== null && 'status' in error) {
      const status = (error as Record<string, unknown>).status as number | undefined
      return status ? this.config.retryableStatusCodes.includes(status) : false
    }

    return false
  }

  /**
   * Check if we should retry based on attempt count
   */
  shouldRetry(attemptNumber: number): boolean {
    return attemptNumber < this.config.maxAttempts
  }
}

/**
 * Network Retry Manager
 */
export class NetworkRetryManager {
  private backoffCalculator: BackoffCalculator
  private requestQueue: Map<string, RetryableRequest> = new Map()
  private retryTimers: Map<string, ReturnType<typeof setTimeout>> = new Map()
  private isOnline: boolean = typeof navigator !== 'undefined' && navigator.onLine

  constructor(config?: Partial<RetryConfig>) {
    const finalConfig = { ...DEFAULT_RETRY_CONFIG, ...config }
    this.backoffCalculator = new BackoffCalculator(finalConfig)

    // Listen for online/offline events
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => this.handleOnline())
      window.addEventListener('offline', () => this.handleOffline())
    }
  }

  /**
   * Execute a request with automatic retry on failure
   */
  async executeWithRetry<T>(
    executeFn: () => Promise<T>,
    options?: {
      maxAttempts?: number
      onRetry?: (attemptNumber: number, delay: number) => void
      onFailed?: (error: unknown) => void
    }
  ): Promise<T> {
    const maxAttempts = options?.maxAttempts ?? DEFAULT_RETRY_CONFIG.maxAttempts
    let lastError: unknown

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await executeFn()
      } catch (error) {
        lastError = error

        if (!this.backoffCalculator.isRetryable(error) || attempt === maxAttempts) {
          options?.onFailed?.(error)
          throw error
        }

        const delay = this.backoffCalculator.calculateDelay(attempt)
        options?.onRetry?.(attempt, delay)

        // Wait before retrying
        await new Promise((resolve) => setTimeout(resolve, delay))
      }
    }

    throw lastError
  }

  /**
   * Queue a request for later retry (when offline)
   */
  queueRequest(
    method: string,
    url: string,
    data?: Record<string, unknown>,
    headers?: Record<string, string>,
    priority: 'high' | 'normal' | 'low' = 'normal'
  ): string {
    const id = this.generateRequestId()
    const request: RetryableRequest = {
      id,
      timestamp: Date.now(),
      method,
      url,
      data,
      headers,
      priority,
      attempts: 0,
    }

    this.requestQueue.set(id, request)
    return id
  }

  /**
   * Dequeue a request
   */
  dequeueRequest(id: string): RetryableRequest | undefined {
    return this.requestQueue.get(id)
  }

  /**
   * Remove a request from queue
   */
  removeRequest(id: string): boolean {
    const removed = this.requestQueue.delete(id)
    const timer = this.retryTimers.get(id)
    if (timer) {
      clearTimeout(timer)
      this.retryTimers.delete(id)
    }
    return removed
  }

  /**
   * Get all queued requests
   */
  getQueuedRequests(): RetryableRequest[] {
    return Array.from(this.requestQueue.values()).sort((a, b) => {
      // Sort by priority first, then by timestamp
      const priorityOrder = { high: 0, normal: 1, low: 2 }
      const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority]
      return priorityDiff !== 0 ? priorityDiff : a.timestamp - b.timestamp
    })
  }

  /**
   * Get queue size
   */
  getQueueSize(): number {
    return this.requestQueue.size
  }

  /**
   * Check if online
   */
  getOnlineStatus(): boolean {
    return this.isOnline
  }

  /**
   * Clear all queued requests
   */
  clearQueue(): void {
    this.requestQueue.clear()
    this.retryTimers.forEach((timer) => clearTimeout(timer))
    this.retryTimers.clear()
  }

  // ── Private Methods ────────────────────────────────────

  private handleOnline(): void {
    this.isOnline = true
    console.log('[NetworkRetryManager] Online - processing queued requests')
    // Trigger event for UI to process queue
    window.dispatchEvent(new CustomEvent('network-online'))
  }

  private handleOffline(): void {
    this.isOnline = false
    console.log('[NetworkRetryManager] Offline - queueing requests')
    window.dispatchEvent(new CustomEvent('network-offline'))
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
}

// Export singleton instance
export const networkRetryManager = new NetworkRetryManager()
