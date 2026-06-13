import { Component } from "react";

/**
 * ErrorBoundary — catches React rendering errors so a single crash
 * never blanks the entire application.
 *
 * Usage:
 *   <ErrorBoundary fallbackLabel="Sandbox">
 *     <Sandbox ... />
 *   </ErrorBoundary>
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error(
      `[ErrorBoundary] ${this.props.fallbackLabel || "Component"} crashed:`,
      error,
      errorInfo
    );
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      const label = this.props.fallbackLabel || "this section";
      return (
        <div className="error-boundary-panel">
          <div className="error-boundary-icon">⚠️</div>
          <h3>Something went wrong in {label}</h3>
          <p className="error-boundary-message">
            {this.state.error?.message || "An unexpected rendering error occurred."}
          </p>
          <button
            className="error-boundary-retry"
            type="button"
            onClick={this.handleRetry}
          >
            Retry
          </button>
          <details className="error-boundary-details">
            <summary>Technical details</summary>
            <pre>
              {this.state.error?.stack || "No stack trace available."}
            </pre>
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}
