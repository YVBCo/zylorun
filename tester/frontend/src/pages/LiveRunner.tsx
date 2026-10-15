import { useState, useEffect, useRef } from 'react';
import { Terminal, Play, Square, Activity, Shield, Download, RefreshCw, Clock, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { apiClient } from '../config';

interface CommandItem {
  id: number;
  name: string;
  executable: string;
  allowed_args: string;
  timeout_seconds: number;
}

interface TargetItem {
  id: number;
  name: string;
  host: string;
  description?: string;
}

interface RunRecord {
  id: number;
  command_id: number;
  target_id: number;
  status: string;
  start_time: string;
  end_time?: string;
  findings: any[];
}

export default function LiveRunner() {
  const [commands, setCommands] = useState<CommandItem[]>([]);
  const [targets, setTargets] = useState<TargetItem[]>([]);
  const [selectedCmd, setSelectedCmd] = useState<number | ''>('');
  const [selectedTarget, setSelectedTarget] = useState<number | ''>('');
  const [status, setStatus] = useState<string>('Idle');
  const [output, setOutput] = useState<string[]>([]);
  const [elapsed, setElapsed] = useState<number>(0);
  const [runHistory, setRunHistory] = useState<RunRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const wsRef = useRef<WebSocket | null>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [cmdRes, targetRes, runsRes] = await Promise.all([
        apiClient.get('/commands/'),
        apiClient.get('/targets/'),
        apiClient.get('/runs/')
      ]);
      setCommands(cmdRes.data);
      setTargets(targetRes.data);
      setRunHistory(runsRes.data);

      if (cmdRes.data.length > 0 && !selectedCmd) {
        setSelectedCmd(cmdRes.data[0].id);
      }
      if (targetRes.data.length > 0 && !selectedTarget) {
        setSelectedTarget(targetRes.data[0].id);
      }
    } catch (err) {
      console.error('Failed to load runner data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    let timer: any;
    if (status === 'Running') {
      timer = setInterval(() => setElapsed(prev => prev + 1), 1000);
    }
    return () => clearInterval(timer);
  }, [status]);

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [output]);

  const startRun = () => {
    if (!selectedCmd || !selectedTarget) return;

    setStatus('Running');
    setOutput([]);
    setElapsed(0);

    const token = localStorage.getItem('access_token') || '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Fallback to localhost:8000 if running in vite dev
    const host = window.location.port === '5173' ? 'localhost:8000' : window.location.host;
    const wsUrl = `${protocol}//${host}/runs/ws/${selectedCmd}/${selectedTarget}?token=${token}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      const cmd = commands.find(c => c.id === Number(selectedCmd));
      let args: string[] = [];
      if (cmd && cmd.allowed_args) {
        try {
          args = JSON.parse(cmd.allowed_args);
        } catch {
          args = [];
        }
      }
      ws.send(JSON.stringify({ args }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.stream) {
          setOutput(prev => [...prev, msg.data]);
        } else if (msg.status) {
          setStatus(msg.status);
          fetchData();
        } else if (msg.error) {
          setOutput(prev => [...prev, `[ERROR] ${msg.error}`]);
          setStatus('Error');
        }
      } catch {
        setOutput(prev => [...prev, event.data]);
      }
    };

    ws.onerror = () => {
      setOutput(prev => [...prev, '[ERROR] WebSocket connection failed.']);
      setStatus('Error');
    };

    ws.onclose = () => {
      setStatus(prev => (prev === 'Running' ? 'Done' : prev));
      fetchData();
    };
  };

  const stopRun = () => {
    if (wsRef.current) {
      wsRef.current.close();
      setStatus('Stopped');
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const getStatusBadge = (s: string) => {
    switch (s.toLowerCase()) {
      case 'running':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 animate-pulse border border-amber-500/20"><Activity className="w-3.5 h-3.5" /> Running</span>;
      case 'pass':
      case 'done':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"><CheckCircle2 className="w-3.5 h-3.5" /> Pass</span>;
      case 'warning':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20"><AlertTriangle className="w-3.5 h-3.5" /> Warning</span>;
      case 'fail':
      case 'error':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-500 border border-rose-500/20"><XCircle className="w-3.5 h-3.5" /> Fail</span>;
      default:
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">Idle</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <Terminal className="w-7 h-7 text-brand-500" />
            Live Security Terminal & Scanner
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Execute approved security scanners and host diagnostics with real-time stdout streaming.
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

      {/* Control Panel */}
      <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col lg:flex-row items-stretch lg:items-center gap-4">
        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
              Select Security Tool
            </label>
            <select
              value={selectedCmd}
              onChange={(e) => setSelectedCmd(Number(e.target.value))}
              disabled={status === 'Running'}
              className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
            >
              {commands.map((cmd) => (
                <option key={cmd.id} value={cmd.id}>
                  {cmd.name} ({cmd.executable})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
              Select Target Host / Endpoint
            </label>
            <select
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(Number(e.target.value))}
              disabled={status === 'Running'}
              className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
            >
              {targets.map((tgt) => (
                <option key={tgt.id} value={tgt.id}>
                  {tgt.name} ({tgt.host})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2 lg:pt-0">
          {status === 'Running' ? (
            <button
              onClick={stopRun}
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-medium text-sm rounded-lg transition shadow-sm"
            >
              <Square className="w-4 h-4 fill-white" /> Stop Scan
            </button>
          ) : (
            <button
              onClick={startRun}
              disabled={!selectedCmd || !selectedTarget}
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-brand-500 hover:bg-brand-600 text-white font-medium text-sm rounded-lg transition shadow-sm disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-white" /> Execute Scan
            </button>
          )}

          <div className="flex items-center gap-4 px-4 py-2 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-800 text-xs">
            <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
              <Clock className="w-4 h-4" />
              <span className="font-mono font-semibold text-slate-700 dark:text-slate-300">{formatTime(elapsed)}</span>
            </div>
            <div>{getStatusBadge(status)}</div>
          </div>
        </div>
      </div>

      {/* Terminal Output */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 shadow-xl overflow-hidden flex flex-col h-[480px]">
        {/* Terminal Header */}
        <div className="px-4 py-2.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-rose-500/80 inline-block"></span>
            <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block"></span>
            <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block"></span>
            <span className="ml-2 font-medium text-slate-300">secrunner://interactive-terminal</span>
          </div>
          <div>Lines: {output.length}</div>
        </div>

        {/* Terminal Body */}
        <div className="flex-1 p-4 font-mono text-xs overflow-y-auto space-y-1 text-slate-300 selection:bg-brand-500 selection:text-white">
          {output.length === 0 && status === 'Idle' && (
            <div className="h-full flex flex-col items-center justify-center text-slate-600">
              <Shield className="w-12 h-12 mb-3 stroke-[1.25] text-slate-700" />
              <p>Terminal ready. Select a security tool and target to begin audit.</p>
            </div>
          )}

          {output.map((line, idx) => {
            let textColor = 'text-slate-300';
            const lower = line.toLowerCase();
            if (lower.includes('error') || lower.includes('fail') || lower.includes('critical') || lower.includes('rejected')) {
              textColor = 'text-rose-400 font-semibold';
            } else if (lower.includes('warning') || lower.includes('warn') || lower.includes('timeout')) {
              textColor = 'text-amber-400';
            } else if (lower.includes('pass') || lower.includes('success') || lower.includes('open')) {
              textColor = 'text-emerald-400';
            }

            return (
              <div key={idx} className={`leading-relaxed ${textColor}`}>
                <span className="text-slate-600 select-none mr-3">{String(idx + 1).padStart(4, '0')}</span>
                {line}
              </div>
            );
          })}
          {status === 'Running' && (
            <div className="text-brand-400 animate-pulse ml-10">_</div>
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>

      {/* Execution History */}
      <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
          Recent Security Audit History
        </h3>
        {runHistory.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">No previous scan records found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4">Run ID</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Findings</th>
                  <th className="py-3 px-4 text-right">Export</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {runHistory.map((run) => (
                  <tr key={run.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4 font-mono font-medium">#{run.id}</td>
                    <td className="py-3.5 px-4">{getStatusBadge(run.status)}</td>
                    <td className="py-3.5 px-4 text-slate-500">{run.start_time ? new Date(run.start_time).toLocaleString() : 'N/A'}</td>
                    <td className="py-3.5 px-4 font-medium">{run.findings?.length || 0} issues</td>
                    <td className="py-3.5 px-4 text-right">
                      <a
                        href={`/reports/${run.id}/csv`}
                        className="inline-flex items-center gap-1.5 text-brand-600 dark:text-brand-400 hover:underline font-medium"
                      >
                        <Download className="w-3.5 h-3.5" /> CSV
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
