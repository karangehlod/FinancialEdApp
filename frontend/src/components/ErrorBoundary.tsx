/**
 * Global Error Boundary — catches unhandled React errors and displays a
 * production-safe fallback UI. Follows WCAG 2.1 AA accessibility guidelines.
 *
 * Key features:
 *   - Logs errors via the production-safe logger (no console in prod)
 *   - Shows stack trace only in development
 *   - Provides "Try Again" (reset) and "Go Home" actions
 *   - Fully responsive (320 px → 1920 px+)
 */

import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertCircle, RefreshCw, Home } from 'lucide-react'
import logger from '@/utils/logger'
import { env } from '@/config/env'

// ── Types ──────────────────────────────────────────────────────────────

interface ErrorBoundaryProps {
  readonly children: ReactNode
  readonly fallback?: ReactNode
}

interface ErrorBoundaryState {
  readonly hasError: boolean
  readonly error: Error | null
  readonly errorInfo: ErrorInfo | null
}

// ── Component ──────────────────────────────────────────────────────────

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(_error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true }
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    logger.error('Unhandled React error caught by ErrorBoundary', {
      message: error.message,
      stack: error.stack ?? '',
      componentStack: errorInfo.componentStack ?? '',
    })
    this.setState({ error, errorInfo })
  }

  private readonly handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div
          className="min-h-screen bg-gradient-to-br from-red-50 to-orange-50 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4"
          role="alert"
          aria-live="assertive"
        >
          <div
            className="w-full bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 sm:p-8"
            style={{ maxWidth: 'var(--content-max-width, 32rem)' }}
          >
            {/* Icon */}
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 dark:bg-red-900/40 rounded-full mb-4">
              <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" aria-hidden="true" />
            </div>

            {/* Heading */}
            <h1 className="text-xl-fluid sm:text-2xl-fluid font-bold text-center text-gray-900 dark:text-gray-100 mb-2">
              Something Went Wrong
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-center mb-6 text-sm-fluid sm:text-base-fluid">
              We encountered an unexpected error. Try refreshing the page or returning to the home screen.
            </p>

            {/* Dev-only error details */}
            {env.isDev && this.state.error && (
              <details className="mb-6 p-4 bg-gray-100 dark:bg-gray-700 rounded text-sm-fluid font-mono text-gray-700 dark:text-gray-300 max-h-40 overflow-auto">
                <summary className="cursor-pointer font-bold mb-2">Error Details</summary>
                <p className="mb-2">{this.state.error.message}</p>
                {this.state.errorInfo?.componentStack && (
                  <pre className="whitespace-pre-wrap break-words">
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </details>
            )}

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
              <button
                type="button"
                onClick={this.handleReset}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                <span className="text-sm-fluid">Try Again</span>
              </button>
              <a
                href="/"
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors text-center focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
              >
                <Home className="w-4 h-4" aria-hidden="true" />
                <span className="text-sm-fluid">Home</span>
              </a>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
