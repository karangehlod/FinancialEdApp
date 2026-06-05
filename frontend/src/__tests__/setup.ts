/**
 * Vitest + Testing Library global test setup.
 * Applied to every test file via setupFiles in vite.config.js.
 */
import { afterEach, beforeAll, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom'

// Clean up mounted components after every test
afterEach(() => {
  cleanup()
})

// Silence noisy console in tests — individual tests can restore if needed
beforeAll(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.spyOn(console, 'warn').mockImplementation(() => {})
})

// ── Browser API Mocks ──────────────────────────────────────────────────────

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

globalThis.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

globalThis.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Prevent navigation-related errors in jsdom
Object.defineProperty(window, 'location', {
  writable: true,
  value: {
    ...window.location,
    replace: vi.fn(),
    assign: vi.fn(),
    reload: vi.fn(),
    origin: 'http://localhost',
  },
})
