import { useState, useEffect } from 'react';
import { 
  Users, Eye, AlertTriangle, ShieldCheck, RefreshCw, Search, 
  Globe, Bug, CheckCircle2, Trash2, Sparkles, ChevronDown, ChevronRight
} from 'lucide-react';
import { apiClient } from '../config';

interface UserItem {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  has_github: boolean;
  repositories_count: number;
  created_at: string | null;
  last_login_at: string | null;
  is_current: boolean;
}

interface UserStatsResponse {
  total_users: number;
  active_users: number;
  admin_users: number;
  current_user: {
    id: number;
    username: string;
    email: string;
    role: string;
  };
  users: UserItem[];
}

interface VisitorStatsResponse {
  total_visits: number;
  unique_visitors: number;
  today_visits: number;
  active_visitors: number;
  top_paths: { path: string; count: number }[];
  recent_visits: {
    id: number;
    visitor_id: string;
    ip_address: string;
    user_agent: string | null;
    path: string;
    referrer: string | null;
    username: string | null;
    created_at: string | null;
  }[];
}

interface ErrorItem {
  id: number;
  error_type: string;
  severity: string;
  message: string;
  stack_trace: string | null;
  path: string | null;
  method: string | null;
  status_code: number | null;
  username: string | null;
  resolved: boolean;
  created_at: string | null;
}

interface ErrorStatsResponse {
  total_errors: number;
  critical_errors: number;
  warning_errors: number;
  errors: ErrorItem[];
}

export default function Admin() {
  const [activeTab, setActiveTab] = useState<'users' | 'visitors' | 'errors'>('users');
  const [loading, setLoading] = useState<boolean>(true);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [userSearch, setUserSearch] = useState<string>('');
  const [errorSearch, setErrorSearch] = useState<string>('');
  const [expandedErrorIds, setExpandedErrorIds] = useState<Record<number, boolean>>({});

  const [userData, setUserData] = useState<UserStatsResponse | null>(null);
  const [visitorData, setVisitorData] = useState<VisitorStatsResponse | null>(null);
  const [errorData, setErrorData] = useState<ErrorStatsResponse | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [uRes, vRes, eRes] = await Promise.allSettled([
        apiClient.get('/admin/users'),
        apiClient.get('/admin/visitors/stats'),
        apiClient.get('/admin/errors')
      ]);

      if (uRes.status === 'fulfilled') setUserData(uRes.value.data);
      if (vRes.status === 'fulfilled') setVisitorData(vRes.value.data);
      if (eRes.status === 'fulfilled') setErrorData(eRes.value.data);
    } catch (err) {
      console.error('Failed to load admin telemetry', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    let interval: any = null;
    if (autoRefresh) {
      interval = setInterval(fetchData, 10000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const triggerTestError = async () => {
    try {
      setActionNotice('Injecting diagnostic test telemetry event...');
      await apiClient.post('/admin/errors/test');
      await fetchData();
      setActionNotice('Test error registered and verified in live error monitor.');
      setTimeout(() => setActionNotice(null), 4000);
    } catch (err: any) {
      setActionNotice('Failed to trigger test error: ' + (err.message || err));
    }
  };

  const clearErrors = async () => {
    if (!window.confirm('Are you sure you want to clear all logged software error records?')) return;
    try {
      await apiClient.delete('/admin/errors');
      await fetchData();
      setActionNotice('Software error logs successfully purged.');
      setTimeout(() => setActionNotice(null), 4000);
    } catch (err: any) {
      setActionNotice('Failed to clear errors: ' + (err.message || err));
    }
  };

  const toggleErrorExpand = (id: number) => {
    setExpandedErrorIds(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredUsers = (userData?.users || []).filter(u => {
    if (!userSearch.trim()) return true;
    const q = userSearch.toLowerCase();
    return u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q) || u.role.toLowerCase().includes(q);
  });

  const filteredErrors = (errorData?.errors || []).filter(e => {
    if (!errorSearch.trim()) return true;
    const q = errorSearch.toLowerCase();
    return e.message.toLowerCase().includes(q) || e.error_type.toLowerCase().includes(q) || (e.path && e.path.toLowerCase().includes(q));
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Header & Session Pill */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 border border-slate-800 rounded-2xl p-6 shadow-sm backdrop-blur">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Admin & Platform Telemetry</h1>
              <p className="text-xs text-slate-400">
                Live monitoring of registered accounts, active visitors, and system runtime health.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {userData?.current_user && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Logged in as: <strong className="text-white">{userData.current_user.username}</strong> ({userData.current_user.role})</span>
            </div>
          )}

          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
              autoRefresh 
                ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' 
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}
            title="Toggle 10-second automatic background refresh"
          >
            Auto-refresh: {autoRefresh ? 'ON (10s)' : 'PAUSED'}
          </button>

          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-medium border border-slate-700 transition shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {actionNotice && (
        <div className="p-3 bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 rounded-xl text-xs flex items-center gap-2 animate-fadeIn">
          <Sparkles className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* Primary KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div 
          onClick={() => setActiveTab('users')}
          className={`cursor-pointer p-5 rounded-2xl border transition-all ${
            activeTab === 'users' 
              ? 'bg-slate-900 border-emerald-500/50 shadow-lg shadow-emerald-500/5 ring-1 ring-emerald-500/20' 
              : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-semibold tracking-wider">Registered Users</span>
            <Users className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {userData?.total_users ?? 0}
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-1.5">
            <span className="text-emerald-400 font-semibold">{userData?.active_users ?? 0} active</span>
            <span>•</span>
            <span>{userData?.admin_users ?? 0} admins</span>
          </div>
        </div>

        <div 
          onClick={() => setActiveTab('visitors')}
          className={`cursor-pointer p-5 rounded-2xl border transition-all ${
            activeTab === 'visitors' 
              ? 'bg-slate-900 border-cyan-500/50 shadow-lg shadow-cyan-500/5 ring-1 ring-cyan-500/20' 
              : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-semibold tracking-wider">Total Software Visits</span>
            <Eye className="w-5 h-5 text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {visitorData?.total_visits ?? 0}
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-1.5">
            <span className="text-cyan-400 font-semibold">{visitorData?.unique_visitors ?? 0} unique</span>
            <span>•</span>
            <span>{visitorData?.today_visits ?? 0} today</span>
          </div>
        </div>

        <div 
          onClick={() => setActiveTab('visitors')}
          className="p-5 rounded-2xl border bg-slate-900/50 border-slate-800"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-semibold tracking-wider">Active Live Visitors</span>
            <Globe className="w-5 h-5 text-blue-400" />
          </div>
          <div className="text-3xl font-extrabold text-blue-400 flex items-center gap-2">
            <span>{visitorData?.active_visitors ?? 0}</span>
            <span className="w-2.5 h-2.5 rounded-full bg-blue-400 animate-ping" />
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Detected within the last 15 minutes
          </div>
        </div>

        <div 
          onClick={() => setActiveTab('errors')}
          className={`cursor-pointer p-5 rounded-2xl border transition-all ${
            activeTab === 'errors' 
              ? 'bg-slate-900 border-rose-500/50 shadow-lg shadow-rose-500/5 ring-1 ring-rose-500/20' 
              : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-semibold tracking-wider">Software Errors</span>
            <AlertTriangle className={`w-5 h-5 ${(errorData?.total_errors ?? 0) > 0 ? 'text-rose-400' : 'text-emerald-400'}`} />
          </div>
          <div className="text-3xl font-extrabold text-white flex items-center gap-2">
            <span>{errorData?.total_errors ?? 0}</span>
            {(errorData?.total_errors ?? 0) === 0 ? (
              <span className="text-xs font-normal text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/30">Healthy</span>
            ) : (
              <span className="text-xs font-normal text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/30">Issues</span>
            )}
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-1.5">
            <span className="text-rose-400 font-semibold">{errorData?.critical_errors ?? 0} critical</span>
            <span>•</span>
            <span>{errorData?.warning_errors ?? 0} warnings</span>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab('users')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'users'
              ? 'border-emerald-500 text-emerald-400 bg-slate-900/40 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>User Directory & Logins ({userData?.users.length ?? 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('visitors')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'visitors'
              ? 'border-cyan-500 text-cyan-400 bg-slate-900/40 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Eye className="w-4 h-4" />
          <span>Visitor Traffic Counter ({visitorData?.total_visits ?? 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('errors')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'errors'
              ? 'border-rose-500 text-rose-400 bg-slate-900/40 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Bug className="w-4 h-4" />
          <span>Software Error Monitor ({errorData?.total_errors ?? 0})</span>
        </button>
      </div>

      {/* TAB 1: USER DETAILS */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search users by username, email, or role..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div className="text-xs text-slate-400">
              Showing <strong className="text-white">{filteredUsers.length}</strong> of {userData?.total_users ?? 0} users
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3.5 px-4">User</th>
                    <th className="py-3.5 px-4">Email</th>
                    <th className="py-3.5 px-4">Role</th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4">Repositories</th>
                    <th className="py-3.5 px-4">Last Login</th>
                    <th className="py-3.5 px-4">Registered Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredUsers.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500">
                        No registered users found matching "{userSearch}".
                      </td>
                    </tr>
                  ) : (
                    filteredUsers.map((u) => (
                      <tr 
                        key={u.id}
                        className={`hover:bg-slate-800/40 transition-colors ${
                          u.is_current ? 'bg-emerald-500/[0.04]' : ''
                        }`}
                      >
                        <td className="py-3.5 px-4 font-medium text-white flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-slate-300">
                            {u.username[0].toUpperCase()}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span>{u.username}</span>
                              {u.is_current && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-semibold">
                                  You
                                </span>
                              )}
                            </div>
                            <span className="text-[10px] text-slate-500">ID #{u.id}</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-slate-300 font-mono text-[11px]">{u.email}</td>
                        <td className="py-3.5 px-4">
                          <span className={`px-2 py-0.5 rounded-full font-medium ${
                            u.role === 'Admin' 
                              ? 'bg-purple-500/10 text-purple-400 border border-purple-500/30' 
                              : 'bg-slate-800 text-slate-300 border border-slate-700'
                          }`}>
                            {u.role}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          {u.is_active ? (
                            <span className="inline-flex items-center gap-1.5 text-emerald-400 font-medium">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                              Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 text-slate-500">
                              <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                              Disabled
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded font-semibold border border-slate-700/60">
                            {u.repositories_count} connected
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                          {u.last_login_at 
                            ? new Date(u.last_login_at).toLocaleString() 
                            : <span className="text-slate-600 italic">Active in session</span>}
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                          {u.created_at 
                            ? new Date(u.created_at).toLocaleDateString() 
                            : <span className="text-slate-600">Active</span>}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: VISITOR TRAFFIC */}
      {activeTab === 'visitors' && (
        <div className="space-y-6">
          {/* Top visited routes breakdown */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
              <Globe className="w-4 h-4 text-cyan-400" />
              <span>Top Visited Software Routes</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {(visitorData?.top_paths || []).map((tp, idx) => (
                <div key={idx} className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl flex items-center justify-between">
                  <div>
                    <span className="font-mono text-xs text-cyan-300">{tp.path}</span>
                    <p className="text-[10px] text-slate-500 mt-0.5">Route destination</p>
                  </div>
                  <span className="px-2.5 py-1 bg-cyan-500/10 text-cyan-400 rounded-lg font-bold text-xs border border-cyan-500/20">
                    {tp.count} hits
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Real-time visitor logs table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Eye className="w-4 h-4 text-cyan-400" />
                <span>Recent Visitor Activity Feed (Latest 50 visits)</span>
              </h3>
              <span className="text-xs text-slate-400">Total Unique Visitors: <strong className="text-cyan-400">{visitorData?.unique_visitors ?? 0}</strong></span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3.5 px-4">Time</th>
                    <th className="py-3.5 px-4">Path Visited</th>
                    <th className="py-3.5 px-4">Visitor Identifier / IP</th>
                    <th className="py-3.5 px-4">User Session</th>
                    <th className="py-3.5 px-4">Client / Device</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {(!visitorData?.recent_visits || visitorData.recent_visits.length === 0) ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500">
                        No visitor telemetry captured yet. Visitors browsing the application will appear here automatically.
                      </td>
                    </tr>
                  ) : (
                    visitorData.recent_visits.map((v) => (
                      <tr key={v.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400">
                          {v.created_at ? new Date(v.created_at).toLocaleTimeString() : 'Just now'}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-cyan-400 font-medium">
                          {v.path}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-slate-300">
                          {v.ip_address}
                        </td>
                        <td className="py-3.5 px-4">
                          {v.username ? (
                            <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded font-medium">
                              @{v.username}
                            </span>
                          ) : (
                            <span className="text-slate-500 italic">Anonymous Visitor</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate" title={v.user_agent || ''}>
                          {v.user_agent || 'Web Browser'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: SOFTWARE ERROR MONITOR */}
      {activeTab === 'errors' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Filter errors by message, type, or path..."
                value={errorSearch}
                onChange={(e) => setErrorSearch(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-rose-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={triggerTestError}
                className="px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-medium transition flex items-center gap-1.5 shadow-sm"
                title="Generates a verification error to confirm real-time monitoring"
              >
                <Bug className="w-3.5 h-3.5" />
                Trigger Test Error
              </button>

              <button
                onClick={clearErrors}
                disabled={!errorData?.total_errors}
                className="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-lg text-xs font-medium transition flex items-center gap-1.5 disabled:opacity-40"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear Errors
              </button>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3.5 px-4 w-10"></th>
                    <th className="py-3.5 px-4">Severity</th>
                    <th className="py-3.5 px-4">Error Type</th>
                    <th className="py-3.5 px-4">Message</th>
                    <th className="py-3.5 px-4">Path / Method</th>
                    <th className="py-3.5 px-4">User</th>
                    <th className="py-3.5 px-4">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredErrors.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-slate-400">
                        <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                        <span className="font-semibold text-white">No software errors reported!</span>
                        <p className="text-xs text-slate-500 mt-1">
                          All backend and frontend services are running cleanly with zero unhandled exceptions.
                        </p>
                      </td>
                    </tr>
                  ) : (
                    filteredErrors.map((err) => {
                      const isExpanded = !!expandedErrorIds[err.id];
                      return (
                        <tr key={err.id} className="group hover:bg-slate-800/40 transition-colors">
                          <td className="py-3.5 px-2 text-center">
                            {err.stack_trace && (
                              <button
                                onClick={() => toggleErrorExpand(err.id)}
                                className="p-1 hover:bg-slate-700 rounded text-slate-400 transition"
                                title="Toggle full stack trace"
                              >
                                {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                              </button>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              err.severity === 'CRITICAL'
                                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                                : err.severity === 'WARNING'
                                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                                : 'bg-red-500/10 text-red-400 border border-red-500/30'
                            }`}>
                              {err.severity}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-mono font-semibold text-white">
                            {err.error_type}
                          </td>
                          <td className="py-3.5 px-4 font-medium text-slate-200">
                            <div>{err.message}</div>
                            {isExpanded && err.stack_trace && (
                              <div className="mt-2 p-3 bg-slate-950 border border-slate-800 rounded-lg font-mono text-[11px] text-rose-300 overflow-x-auto whitespace-pre">
                                {err.stack_trace}
                              </div>
                            )}
                          </td>
                          <td className="py-3.5 px-4 font-mono text-slate-400">
                            {err.method && <span className="text-cyan-400 mr-1.5">{err.method}</span>}
                            <span>{err.path || 'UI Component'}</span>
                          </td>
                          <td className="py-3.5 px-4">
                            {err.username ? (
                              <span className="text-emerald-400 font-medium">@{err.username}</span>
                            ) : (
                              <span className="text-slate-500 italic">System / Client</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                            {err.created_at ? new Date(err.created_at).toLocaleString() : 'Just now'}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
