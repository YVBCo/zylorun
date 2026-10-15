import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("UI Crashed:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen w-screen flex flex-col items-center justify-center bg-gray-900 text-white p-6 font-mono text-center">
          <h1 className="text-4xl text-red-500 mb-4 font-bold">SYSTEM FAILURE</h1>
          <p className="mb-8 text-gray-400">The interface encountered a critical rendering error.</p>
          <pre className="bg-black p-4 rounded text-left text-sm text-red-400 max-w-2xl overflow-auto border border-red-900 shadow-xl">
            {this.state.error && this.state.error.toString()}
          </pre>
          <button 
            onClick={() => window.location.reload()}
            className="mt-8 px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded shadow font-bold transition"
          >
            Reboot Interface
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
