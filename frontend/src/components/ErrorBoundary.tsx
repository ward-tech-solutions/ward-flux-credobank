import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error boundary caught error:', error, errorInfo)

    // Send error to backend for logging
    fetch('/api/v1/log-error', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: error.toString(),
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
      }),
    }).catch(console.error)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-container">
          <div className="error-boundary-content">
            <div className="error-icon">⚠️</div>
            <h1>Something went wrong</h1>
            <p className="error-message">
              We're sorry, but something unexpected happened. The error has been logged
              and our team will look into it.
            </p>
            {this.state.error && (
              <details className="error-details">
                <summary>Technical Details</summary>
                <pre>{this.state.error.toString()}</pre>
              </details>
            )}
            <div className="error-actions">
              <button onClick={this.handleReset} className="btn-primary">
                <i className="fas fa-home"></i>
                Return to Dashboard
              </button>
              <button onClick={() => window.location.reload()} className="btn-secondary">
                <i className="fas fa-redo"></i>
                Reload Page
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
