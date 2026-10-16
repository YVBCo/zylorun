import { useEffect, Component, type ErrorInfo, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import './config'; // Ensures axios interceptor is loaded

// Statically import pages so all routes and icons are bundled reliably
// This completely prevents chunk load 404 errors across production deployments
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Onboarding from './pages/Onboarding';
import RiskPassport from './pages/RiskPassport';
import CommitAudit from './pages/CommitAudit';
import ProjectHub from './pages/ProjectHub';
import LiveRunner from './pages/LiveRunner';
import LogAnalyzer from './pages/LogAnalyzer';
import EdgeDiagnostics from './pages/EdgeDiagnostics';
import TargetSettings from './pages/TargetSettings';
import SystemAssurance from './pages/SystemAssurance';
import Admin from './pages/Admin';

// Application Error Boundary to catch unexpected runtime exceptions and provide clean recovery
interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class AppErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled app error in AppErrorBoundary:', error, errorInfo);
    try {
      import('./config').then(({ apiClient }) => {
        apiClient.post('/admin/log-error', {
          error_type: 'REACT_APP_CRASH',
          severity: 'CRITICAL',
          message: error.message || 'React component crash',
          stack_trace: `${error.stack || ''}\nComponent Stack: ${errorInfo.componentStack || ''}`,
          path: window.location.pathname,
          method: 'UI_RENDER'
        }).catch(() => {});
      });
    } catch (_) {}
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 p-6">
          <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center shadow-xl space-y-4">
            <div className="w-12 h-12 rounded-full bg-brand-500/10 text-brand-400 mx-auto flex items-center justify-center font-bold text-xl">
              !
            </div>
            <h2 className="text-xl font-bold text-white">Application Notice</h2>
            <p className="text-sm text-slate-400">
              An error occurred while loading this view. You can refresh to reload the application.
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="w-full py-2.5 px-4 bg-brand-500 hover:bg-brand-600 text-white font-medium rounded-lg transition-colors shadow-sm text-sm"
            >
              Refresh Application
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function TokenExtractor() {
  const location = useLocation();
  useEffect(() => {
    const hash = window.location.hash;
    if (hash.includes('token=')) {
      const params = new URLSearchParams(hash.substring(1));
      const token = params.get('token');
      if (token) {
        localStorage.setItem('access_token', token);
        window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
      }
    }
  }, [location]);
  return null;
}

function VisitorTracker() {
  const location = useLocation();
  useEffect(() => {
    try {
      let visitorId = localStorage.getItem('zylorun_visitor_id');
      if (!visitorId) {
        visitorId = 'vis_' + Math.random().toString(36).substring(2, 12);
        localStorage.setItem('zylorun_visitor_id', visitorId);
      }
      import('./config').then(({ apiClient }) => {
        apiClient.post('/admin/track-visit', {
          visitor_id: visitorId,
          path: location.pathname,
          referrer: document.referrer || null,
          user_agent: navigator.userAgent
        }).catch(() => {});
      });
    } catch (_) {}
  }, [location.pathname]);
  return null;
}

function App() {
  return (
    <AppErrorBoundary>
      <ThemeProvider>
        <BrowserRouter>
          <TokenExtractor />
          <VisitorTracker />
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Standalone Protected Admin Security Portal */}
            <Route path="/flash-admin" element={<Admin />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="/admin/login" element={<Admin />} />

            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/hub" element={<ProjectHub />} />
              <Route path="/hub/:repositoryId" element={<ProjectHub />} />
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/passport" element={<RiskPassport />} />
              <Route path="/repositories/:repositoryId/scans/:scanId/audit" element={<CommitAudit />} />
              <Route path="/scanner" element={<LiveRunner />} />
              <Route path="/analyzer" element={<LogAnalyzer />} />
              <Route path="/diagnostics" element={<EdgeDiagnostics />} />
              <Route path="/assurance" element={<SystemAssurance />} />
              <Route path="/settings/targets" element={<TargetSettings />} />

              {/* Legacy SecRunner & testing compatibility redirects */}
              <Route path="/tests" element={<Navigate to="/assurance" replace />} />
              <Route path="/system-tests" element={<Navigate to="/assurance" replace />} />
              <Route path="/run" element={<Navigate to="/scanner" replace />} />
              <Route path="/analyze" element={<Navigate to="/analyzer" replace />} />
              <Route path="/command-run" element={<Navigate to="/diagnostics" replace />} />
              <Route path="/command-prompt" element={<Navigate to="/scanner" replace />} />
              <Route path="/manage-commands" element={<Navigate to="/settings/targets" replace />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </AppErrorBoundary>
  );
}

export default App;
