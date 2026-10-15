import { useState, useEffect, type FormEvent } from 'react';
import { Plus, Trash2, Server, Terminal, X, RefreshCw } from 'lucide-react';
import { apiClient } from '../config';

interface TargetItem {
  id: number;
  name: string;
  host: string;
  description?: string;
  created_at?: string;
}

interface CommandItem {
  id: number;
  name: string;
  executable: string;
  allowed_args: string;
  timeout_seconds: number;
  regex_rules: string;
}

export default function TargetSettings() {
  const [targets, setTargets] = useState<TargetItem[]>([]);
  const [commands, setCommands] = useState<CommandItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  
  // Modals
  const [addTargetOpen, setAddTargetOpen] = useState<boolean>(false);
  const [newTargetName, setNewTargetName] = useState<string>('');
  const [newTargetHost, setNewTargetHost] = useState<string>('');
  const [newTargetDesc, setNewTargetDesc] = useState<string>('');
  const [targetError, setTargetError] = useState<string>('');

  const [addCmdOpen, setAddCmdOpen] = useState<boolean>(false);
  const [newCmdName, setNewCmdName] = useState<string>('');
  const [newCmdExec, setNewCmdExec] = useState<string>('ping');
  const [newCmdArgs, setNewCmdArgs] = useState<string>('-c, 4, -n, 4');
  const [newCmdTimeout, setNewCmdTimeout] = useState<number>(30);
  const [cmdError, setCmdError] = useState<string>('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [tRes, cRes] = await Promise.all([
        apiClient.get('/targets/'),
        apiClient.get('/commands/')
      ]);
      setTargets(tRes.data);
      setCommands(cRes.data);
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateTarget = async (e: FormEvent) => {
    e.preventDefault();
    setTargetError('');
    try {
      await apiClient.post('/targets/', {
        name: newTargetName,
        host: newTargetHost,
        description: newTargetDesc
      });
      setAddTargetOpen(false);
      setNewTargetName('');
      setNewTargetHost('');
      setNewTargetDesc('');
      fetchData();
    } catch (err: any) {
      setTargetError(err.response?.data?.detail || err.message || 'Failed to create target.');
    }
  };

  const handleDeleteTarget = async (id: number) => {
    if (!confirm('Are you sure you want to delete this target?')) return;
    try {
      await apiClient.delete(`/targets/${id}`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete target.');
    }
  };

  const handleCreateCommand = async (e: FormEvent) => {
    e.preventDefault();
    setCmdError('');
    try {
      const argsArray = newCmdArgs.split(',').map(s => s.trim()).filter(Boolean);
      await apiClient.post('/commands/', {
        name: newCmdName,
        executable: newCmdExec,
        allowed_args: argsArray,
        timeout_seconds: Number(newCmdTimeout),
        regex_rules: { rules: [] }
      });
      setAddCmdOpen(false);
      setNewCmdName('');
      setNewCmdArgs('-c, 4');
      fetchData();
    } catch (err: any) {
      setCmdError(err.response?.data?.detail || err.message || 'Failed to register command.');
    }
  };

  const handleDeleteCommand = async (id: number) => {
    if (!confirm('Are you sure you want to delete this command configuration?')) return;
    try {
      await apiClient.delete(`/commands/${id}`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete command.');
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <Server className="w-7 h-7 text-brand-500" />
            Security Targets & Approved Tools
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Manage target hosts, IP inventory scopes, and approved operating system security tools.
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 transition disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Target Hosts Section */}
      <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Registered Target Hosts</h3>
            <p className="text-xs text-slate-500">Endpoints approved for automated security scanning</p>
          </div>
          <button
            onClick={() => setAddTargetOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-lg shadow-sm transition"
          >
            <Plus className="w-4 h-4" /> Add Target Host
          </button>
        </div>

        {targets.length === 0 ? (
          <p className="text-xs text-slate-500 py-4">No target hosts configured yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
            {targets.map((tgt) => (
              <div key={tgt.id} className="p-4 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 rounded-xl relative group">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100">{tgt.name}</h4>
                    <p className="font-mono text-xs text-brand-600 dark:text-brand-400 mt-0.5">{tgt.host}</p>
                    {tgt.description && (
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">{tgt.description}</p>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteTarget(tgt.id)}
                    className="p-1.5 text-slate-400 hover:text-rose-500 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/20 transition"
                    title="Delete target"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Command Configurations Section */}
      <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Approved Security Tools & CLI Profiles</h3>
            <p className="text-xs text-slate-500">Allowlisted executables and argument boundaries for sandboxed execution</p>
          </div>
          <button
            onClick={() => setAddCmdOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 dark:bg-slate-700 hover:bg-slate-700 dark:hover:bg-slate-600 text-white text-xs font-semibold rounded-lg shadow-sm transition"
          >
            <Plus className="w-4 h-4" /> Register Tool Profile
          </button>
        </div>

        {commands.length === 0 ? (
          <p className="text-xs text-slate-500 py-4">No tools registered yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
            {commands.map((cmd) => (
              <div key={cmd.id} className="p-4 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 rounded-xl relative group">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-brand-500" />
                      {cmd.name}
                    </h4>
                    <p className="font-mono text-xs text-slate-500 dark:text-slate-400 mt-1">Binary: <span className="text-slate-700 dark:text-slate-200 font-semibold">{cmd.executable}</span></p>
                    <p className="text-[11px] text-slate-500 mt-1 truncate">
                      Args: <span className="font-mono text-slate-600 dark:text-slate-300">{cmd.allowed_args}</span>
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1">Timeout: {cmd.timeout_seconds}s</p>
                  </div>
                  <button
                    onClick={() => handleDeleteCommand(cmd.id)}
                    className="p-1.5 text-slate-400 hover:text-rose-500 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/20 transition"
                    title="Delete tool"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Target Modal */}
      {addTargetOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h4 className="font-bold text-base text-slate-900 dark:text-white">Register Target Host</h4>
              <button onClick={() => setAddTargetOpen(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            {targetError && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 rounded-lg text-rose-600 dark:text-rose-400 text-xs">
                {targetError}
              </div>
            )}

            <form onSubmit={handleCreateTarget} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold uppercase text-slate-500 mb-1">Target Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Production API Gateway"
                  value={newTargetName}
                  onChange={(e) => setNewTargetName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              <div>
                <label className="block font-semibold uppercase text-slate-500 mb-1">Host / Domain / IP</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., api.example.com or 192.168.1.10"
                  value={newTargetHost}
                  onChange={(e) => setNewTargetHost(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg font-mono text-slate-800 dark:text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              <div>
                <label className="block font-semibold uppercase text-slate-500 mb-1">Description (Optional)</label>
                <input
                  type="text"
                  placeholder="Internal staging cluster"
                  value={newTargetDesc}
                  onChange={(e) => setNewTargetDesc(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setAddTargetOpen(false)}
                  className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-semibold"
                >
                  Save Target
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Command Modal */}
      {addCmdOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h4 className="font-bold text-base text-slate-900 dark:text-white">Register Tool Profile</h4>
              <button onClick={() => setAddCmdOpen(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            {cmdError && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 rounded-lg text-rose-600 dark:text-rose-400 text-xs">
                {cmdError}
              </div>
            )}

            <form onSubmit={handleCreateCommand} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold uppercase text-slate-500 mb-1">Tool Profile Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Quick Nmap Top 10"
                  value={newCmdName}
                  onChange={(e) => setNewCmdName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              <div>
                <label className="block font-semibold uppercase text-slate-500 mb-1">Approved Executable</label>
                <select
                  value={newCmdExec}
                  onChange={(e) => setNewCmdExec(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                >
                  <option value="ping">ping</option>
                  <option value="curl">curl</option>
                  <option value="nmap">nmap</option>
                  <option value="eslint">eslint</option>
                  <option value="git">git</option>
                  <option value="openssl">openssl</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold uppercase text-slate-500 mb-1">Allowed Arguments (comma-separated)</label>
                <input
                  type="text"
                  required
                  placeholder="-c, 4, -n, 4"
                  value={newCmdArgs}
                  onChange={(e) => setNewCmdArgs(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg font-mono text-slate-800 dark:text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              <div>
                <label className="block font-semibold uppercase text-slate-500 mb-1">Timeout (seconds)</label>
                <input
                  type="number"
                  min="5"
                  max="300"
                  value={newCmdTimeout}
                  onChange={(e) => setNewCmdTimeout(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setAddCmdOpen(false)}
                  className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-semibold"
                >
                  Save Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
