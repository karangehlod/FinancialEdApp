import React from 'react'
import { AlertCircle, RefreshCw, Home } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

/**
 * ErrorBoundary Component
 * Catches JavaScript errors in child components and displays a fallback UI
 * Follows React best practices for error handling
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo)
    this.setState({
      error,
      errorInfo,
    })
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-red-50 to-orange-50 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
          <div className="w-full bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8" style={{ maxWidth: 'var(--content-max-width)' }}>
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 dark:bg-red-900/40 rounded-full mb-4">
              <AlertCircle className="text-red-600 dark:text-red-400" size={24} />
            </div>
            <h1 className="text-2xl font-bold text-center text-gray-900 dark:text-gray-100 mb-2">
              Something Went Wrong
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-center mb-6">
              We encountered an unexpected error. Try refreshing the page or returning to the home screen.
            </p>
            
            {/* Error Details (dev only) */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mb-6 p-4 bg-gray-100 dark:bg-gray-700 rounded text-sm font-mono text-gray-700 dark:text-gray-300 max-h-40 overflow-auto">
                <summary className="cursor-pointer font-bold mb-2">Error Details</summary>
                <p className="mb-2">{this.state.error.toString()}</p>
                {this.state.errorInfo && (
                  <pre className="whitespace-pre-wrap break-words">
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </details>
            )}

            <div className="flex gap-4">
              <button
                onClick={this.handleReset}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <RefreshCw size={18} />
                Try Again
              </button>
              <a
                href="/"
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors text-center"
              >
                <Home size={18} />
                Home
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
