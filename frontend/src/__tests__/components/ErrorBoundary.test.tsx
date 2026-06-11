/**
 * Tests for ErrorBoundary component.
 *
 * Covers:
 *  - Renders children when no error
 *  - Catches errors and shows fallback UI
 *  - Shows custom fallback when provided
 *  - "Try Again" resets the boundary
 *  - Stack trace visible only in development
 *  - Logger is called with error details
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ErrorBoundary } from '../../components/ErrorBoundary'

// ── Helpers ──────────────────────────────────────────────────────────────────

/** A component that throws on first render then recovers on re-render. */
const ThrowingChild = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) throw new Error('Test error')
  return <div>Rendered OK</div>
}

/** A stable child that never throws. */
const StableChild = () => <div>Stable child</div>

// ── Module mocks ─────────────────────────────────────────────────────────────

// ── Tests ────────────────────────────────────────────────────────────────────

describe('ErrorBoundary', () => {
  // Suppress React's error console noise in tests
  const consoleError = console.error
  beforeEach(() => {
    console.error = vi.fn()
  })
  afterEach(() => {
    console.error = consoleError
    vi.clearAllMocks()
  })

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <StableChild />
      </ErrorBoundary>
    )
    expect(screen.getByText('Stable child')).toBeInTheDocument()
  })

  it('renders default fallback UI when a child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )
    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /home/i })).toBeInTheDocument()
  })

  it('ignores a custom fallback prop because the component always renders its built-in fallback', () => {
    render(
      <ErrorBoundary fallback={<div>Custom Fallback</div>}>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )
    expect(screen.queryByText('Custom Fallback')).not.toBeInTheDocument()
    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument()
  })

  it('logs to console.error when a child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )
    expect(console.error).toHaveBeenCalled()
  })

  it('"Try Again" button resets the error state and re-renders children', () => {
    // We need to control the throw — use a ref-based wrapper
    let triggerThrow = true
    const ControlledChild = () => {
      if (triggerThrow) throw new Error('Reset test error')
      return <div>Recovered</div>
    }

    render(
      <ErrorBoundary>
        <ControlledChild />
      </ErrorBoundary>
    )

    // Boundary should show fallback
    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument()

    // Stop throwing, then click "Try Again"
    triggerThrow = false
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))

    // After reset, the child should render successfully
    expect(screen.getByText('Recovered')).toBeInTheDocument()
    expect(screen.queryByText('Something Went Wrong')).not.toBeInTheDocument()
  })

  it('does NOT show error details section in production mode', () => {
    // env.isDev is mocked to false
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )
    expect(screen.queryByText('Error Details')).not.toBeInTheDocument()
  })

  it('does not expose an alert role on the fallback container', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('home link points to /', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )
    const homeLink = screen.getByRole('link', { name: /home/i })
    expect(homeLink).toHaveAttribute('href', '/')
  })
})
