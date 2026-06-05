/**
 * Tests for NetworkRetryManager and BackoffCalculator.
 *
 * Covers:
 *  - BackoffCalculator: delay increases exponentially with jitter
 *  - BackoffCalculator: identifies retryable errors (network + status codes)
 *  - BackoffCalculator: shouldRetry respects maxAttempts
 *  - NetworkRetryManager: retries on retryable failure then succeeds
 *  - NetworkRetryManager: does not retry on non-retryable error
 *  - NetworkRetryManager: respects maxAttempts and throws after exhaustion
 *  - NetworkRetryManager: calls onRetry callback with attempt number and delay
 *  - NetworkRetryManager: calls onFailed callback on terminal failure
 *  - NetworkRetryManager: request queue operations (enqueue, dequeue, remove, clear)
 *  - NetworkRetryManager: getOnlineStatus reflects navigator.onLine
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  BackoffCalculator,
  NetworkRetryManager,
  DEFAULT_RETRY_CONFIG,
} from '../../services/networkRetryManager'

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Create a mock error with an HTTP status code. */
const httpError = (status: number): object => ({ status, message: `HTTP ${status}` })

/** Create a native TypeError that looks like a network fetch failure. */
const networkError = (): TypeError => new TypeError('Failed to fetch: network issue')

// ── BackoffCalculator ─────────────────────────────────────────────────────────

describe('BackoffCalculator', () => {
  const calc = new BackoffCalculator()

  it('first attempt delay is approximately initialDelayMs', () => {
    const delay = calc.calculateDelay(1)
    // With up to 10% jitter, delay must be in [1000, 1100]
    expect(delay).toBeGreaterThanOrEqual(DEFAULT_RETRY_CONFIG.initialDelayMs)
    expect(delay).toBeLessThanOrEqual(
      DEFAULT_RETRY_CONFIG.initialDelayMs * (1 + DEFAULT_RETRY_CONFIG.jitterFactor)
    )
  })

  it('delay grows with attempt number', () => {
    const delay1 = calc.calculateDelay(1)
    const delay2 = calc.calculateDelay(2)
    const delay3 = calc.calculateDelay(3)
    // Allow for jitter overlap but generally increasing
    expect(delay2).toBeGreaterThan(delay1 * 0.9)
    expect(delay3).toBeGreaterThan(delay2 * 0.9)
  })

  it('delay is capped at maxDelayMs', () => {
    const delay = calc.calculateDelay(100) // very high attempt
    expect(delay).toBeLessThanOrEqual(
      DEFAULT_RETRY_CONFIG.maxDelayMs * (1 + DEFAULT_RETRY_CONFIG.jitterFactor)
    )
  })

  describe('isRetryable', () => {
    it.each(DEFAULT_RETRY_CONFIG.retryableStatusCodes)(
      'returns true for status code %i',
      (code) => {
        expect(calc.isRetryable(httpError(code))).toBe(true)
      }
    )

    it('returns false for non-retryable status 400', () => {
      expect(calc.isRetryable(httpError(400))).toBe(false)
    })

    it('returns false for non-retryable status 401', () => {
      expect(calc.isRetryable(httpError(401))).toBe(false)
    })

    it('returns false for non-retryable status 403', () => {
      expect(calc.isRetryable(httpError(403))).toBe(false)
    })

    it('returns true for TypeError with "fetch" in message', () => {
      expect(calc.isRetryable(networkError())).toBe(true)
    })

    it('returns false for generic Error', () => {
      expect(calc.isRetryable(new Error('something else'))).toBe(false)
    })
  })

  describe('shouldRetry', () => {
    it('returns true when attempt < maxAttempts', () => {
      expect(calc.shouldRetry(DEFAULT_RETRY_CONFIG.maxAttempts - 1)).toBe(true)
    })

    it('returns false when attempt equals maxAttempts', () => {
      expect(calc.shouldRetry(DEFAULT_RETRY_CONFIG.maxAttempts)).toBe(false)
    })

    it('returns false when attempt exceeds maxAttempts', () => {
      expect(calc.shouldRetry(DEFAULT_RETRY_CONFIG.maxAttempts + 5)).toBe(false)
    })
  })
})

// ── NetworkRetryManager ───────────────────────────────────────────────────────

describe('NetworkRetryManager', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('returns result immediately on first successful attempt', async () => {
    const manager = new NetworkRetryManager({ initialDelayMs: 10 })
    const fn = vi.fn().mockResolvedValue('data')

    const result = await manager.executeWithRetry(fn)
    expect(result).toBe('data')
    expect(fn).toHaveBeenCalledOnce()
  })

  it('retries on retryable error and succeeds on second attempt', async () => {
    const manager = new NetworkRetryManager({ initialDelayMs: 10, maxDelayMs: 10 })
    const fn = vi
      .fn()
      .mockRejectedValueOnce(httpError(500))
      .mockResolvedValue('recovered')

    const promise = manager.executeWithRetry(fn, { maxAttempts: 3 })
    // Advance all timers so retry delay passes
    await vi.runAllTimersAsync()
    const result = await promise
    expect(result).toBe('recovered')
    expect(fn).toHaveBeenCalledTimes(2)
  })

  it('throws immediately on non-retryable error without retrying', async () => {
    const manager = new NetworkRetryManager({ initialDelayMs: 10 })
    const nonRetryable = httpError(403)
    const fn = vi.fn().mockRejectedValue(nonRetryable)

    await expect(manager.executeWithRetry(fn)).rejects.toEqual(nonRetryable)
    expect(fn).toHaveBeenCalledOnce()
  })

  it('throws after exhausting all retry attempts', async () => {
    const manager = new NetworkRetryManager({ initialDelayMs: 10, maxDelayMs: 10, maxAttempts: 2 })
    const retryableError = httpError(503)
    const fn = vi.fn().mockRejectedValue(retryableError)

    // Wrap in a single promise that we advance timers alongside
    let caughtError: unknown
    const promise = manager
      .executeWithRetry(fn, { maxAttempts: 2 })
      .catch((e) => { caughtError = e })
    await vi.runAllTimersAsync()
    await promise
    expect(caughtError).toEqual(retryableError)
    expect(fn).toHaveBeenCalledTimes(2)
  })

  it('calls onRetry callback for each retry with attempt number and delay', async () => {
    const manager = new NetworkRetryManager({ initialDelayMs: 10, maxDelayMs: 10 })
    const fn = vi
      .fn()
      .mockRejectedValueOnce(httpError(500))
      .mockResolvedValue('ok')

    const onRetry = vi.fn()
    const promise = manager.executeWithRetry(fn, { maxAttempts: 3, onRetry })
    await vi.runAllTimersAsync()
    await promise

    expect(onRetry).toHaveBeenCalledOnce()
    const [attemptNum, delay] = onRetry.mock.calls[0] as [number, number]
    expect(attemptNum).toBe(1)
    expect(delay).toBeGreaterThan(0)
  })

  it('calls onFailed callback on terminal failure', async () => {
    const manager = new NetworkRetryManager({ initialDelayMs: 10, maxDelayMs: 10, maxAttempts: 1 })
    const err = httpError(503)
    const fn = vi.fn().mockRejectedValue(err)
    const onFailed = vi.fn()

    let caughtError: unknown
    const promise = manager
      .executeWithRetry(fn, { maxAttempts: 1, onFailed })
      .catch((e) => { caughtError = e })
    await vi.runAllTimersAsync()
    await promise
    expect(caughtError).toBeDefined()
    expect(onFailed).toHaveBeenCalledWith(err)
  })

  // ── Queue operations ────────────────────────────────────────────────────────

  describe('request queue', () => {
    it('queueRequest returns a unique id and adds to queue', () => {
      const manager = new NetworkRetryManager()
      const id = manager.queueRequest('GET', '/api/test')
      expect(typeof id).toBe('string')
      expect(id).toMatch(/^req_/)
      expect(manager.getQueueSize()).toBe(1)
    })

    it('dequeueRequest returns the queued request', () => {
      const manager = new NetworkRetryManager()
      const id = manager.queueRequest('POST', '/api/data', { key: 'value' })
      const req = manager.dequeueRequest(id)
      expect(req).toBeDefined()
      expect(req?.method).toBe('POST')
      expect(req?.url).toBe('/api/data')
    })

    it('removeRequest removes a queued request', () => {
      const manager = new NetworkRetryManager()
      const id = manager.queueRequest('DELETE', '/api/item/1')
      expect(manager.getQueueSize()).toBe(1)
      const removed = manager.removeRequest(id)
      expect(removed).toBe(true)
      expect(manager.getQueueSize()).toBe(0)
    })

    it('getQueuedRequests sorts by priority then timestamp', () => {
      const manager = new NetworkRetryManager()
      manager.queueRequest('GET', '/low', undefined, undefined, 'low')
      manager.queueRequest('GET', '/high', undefined, undefined, 'high')
      manager.queueRequest('GET', '/normal', undefined, undefined, 'normal')

      const requests = manager.getQueuedRequests()
      expect(requests).toHaveLength(3)
      expect(requests[0]!.priority).toBe('high')
      expect(requests[1]!.priority).toBe('normal')
      expect(requests[2]!.priority).toBe('low')
    })

    it('clearQueue empties all requests', () => {
      const manager = new NetworkRetryManager()
      manager.queueRequest('GET', '/a')
      manager.queueRequest('GET', '/b')
      expect(manager.getQueueSize()).toBe(2)
      manager.clearQueue()
      expect(manager.getQueueSize()).toBe(0)
    })
  })

  // ── Online status ─────────────────────────────────────────────────────────

  it('getOnlineStatus reflects navigator.onLine on construction', () => {
    const manager = new NetworkRetryManager()
    // jsdom sets navigator.onLine = true by default
    expect(manager.getOnlineStatus()).toBe(true)
  })
})
