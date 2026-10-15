import { useState } from 'react';
import { Globe, RefreshCw, Play } from 'lucide-react';
import { apiClient } from '../config';

interface DiagnosticResult {
  success: boolean;
  url: string;
  status_code: number;
  total_time_ms: number;
  ttfb_ms: number;
  content_size_bytes: number;
  speed_grade: 'GREEN' | 'YELLOW' | 'RED';
  status_text: string;
  badge_color: string;
  server: string;
  content_type: string;
  encoding: string;
  redirects: number;
}

const networkPresets = [
  {
    name: 'Cloudflare Edge TLS & DNS',
    url: 'https://1.1.1.1',
    description: 'Measures TCP handshake, TLS negotiation, and routing latency to nearest Anycast edge.'
  },
  {
    name: 'Google Public API Gateway',
    url: 'https://dns.google',
    description: 'Tests DNS resolution round-trip, TLS 1.3 cipher negotiation, and HTTP/2 headers.'
  },
  {
    name: 'GitHub REST API Health',
    url: 'https://api.github.com',
    description: 'Monitors API gateway reachability, rate limiting headers, and geographic routing.'
  }
];

export default function EdgeDiagnostics() {
  const [targetUrl, setTargetUrl] = useState<string>('https://google.com');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<DiagnosticResult | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const runDiagnostic = async (urlToTest?: string) => {
    const url = urlToTest || targetUrl;
    if (!url.trim()) return;

    setLoading(true);
    setResult(null);
    setLogs([
      `[INIT] Commencing edge diagnostic for: ${url}`,
      `[PROBE] Dispatching HTTP request and measuring TTFB...`
    ]);

    try {
      const res = await apiClient.post('/runs/url-speed-test', { url });
      setResult(res.data);
      if (res.data.success) {
        setLogs(prev => [
          ...prev,
          `[HTTP] Response status: ${res.data.status_code}`,
          `[TIMING] Total latency: ${res.data.total_time_ms}ms (TTFB: ${res.data.ttfb_ms}ms)`,
          `[HEADERS] Server: ${res.data.server} | Content-Type: ${res.data.content_type}`,
          `[GRADE] Performance Classification: ${res.data.speed_grade} (${res.data.status_text})`
        ]);
      } else {
        setLogs(prev => [
          ...prev,
          `[FAILED] ${res.data.status_text}`
        ]);
      }
    } catch (err: any) {
      setLogs(prev => [...prev, `[ERROR] Network diagnostic failure: ${err.message || err}`]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
          <Globe className="w-7 h-7 text-brand-500" />
          URL Performance & Edge Diagnostics
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Perform real-time HTTP handshake audits, TTFB latency diagnostics, and edge routing tests against remote endpoints.
        </p>
      </div>

      {/* Target Input */}
      <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Target Web Address / URL
        </label>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <input
            type="text"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 px-4 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm text-slate-800 dark:text-slate-200 font-mono focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
          />
          <button
            onClick={() => runDiagnostic()}
            disabled={loading || !targetUrl.trim()}
            className="inline-flex items-center justify-center gap-2 px-6 py-2.5 bg-brand-500 hover:bg-brand-600 text-white font-medium text-sm rounded-lg transition shadow-sm disabled:opacity-50"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
            <span>Run Diagnostic</span>
          </button>
        </div>

        {/* Presets */}
        <div className="pt-2">
          <p className="text-xs font-semibold uppercase text-slate-400 mb-2">Preset Edge Benchmarks:</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {networkPresets.map((preset, idx) => (
              <div
                key={idx}
                onClick={() => { setTargetUrl(preset.url); runDiagnostic(preset.url); }}
                className="p-3 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 rounded-lg hover:border-brand-500 cursor-pointer transition text-xs group"
              >
                <div className="font-semibold text-slate-800 dark:text-slate-200 group-hover:text-brand-500 transition">
                  {preset.name}
                </div>
                <div className="text-slate-500 dark:text-slate-400 font-mono mt-0.5">{preset.url}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Metrics Cards */}
      {result && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-400">Total Latency</p>
            <p className="text-2xl font-bold font-mono text-brand-500 mt-1">
              {result.total_time_ms} ms
            </p>
            <p className="text-xs text-slate-400 mt-1">Full round-trip duration</p>
          </div>

          <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-400">Time to First Byte (TTFB)</p>
            <p className="text-2xl font-bold font-mono text-slate-800 dark:text-slate-200 mt-1">
              {result.ttfb_ms} ms
            </p>
            <p className="text-xs text-slate-400 mt-1">Server response latency</p>
          </div>

          <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-400">HTTP Status Code</p>
            <p className={`text-2xl font-bold font-mono mt-1 ${result.status_code < 400 ? 'text-emerald-500' : 'text-rose-500'}`}>
              {result.status_code || 'Err'}
            </p>
            <p className="text-xs text-slate-400 mt-1">Redirects: {result.redirects}</p>
          </div>

          <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-400">Performance Rating</p>
            <div className="mt-1">
              <span
                className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase"
                style={{ backgroundColor: `${result.badge_color}20`, color: result.badge_color }}
              >
                {result.speed_grade}: {result.status_text}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-2 truncate">Server: {result.server || 'Hidden'}</p>
          </div>
        </div>
      )}

      {/* Console Log */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 shadow-xl overflow-hidden flex flex-col h-64">
        <div className="px-4 py-2.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
          <span>diagnostic://stdout-telemetry</span>
          <span>{loading ? 'Testing...' : 'Ready'}</span>
        </div>
        <div className="flex-1 p-4 font-mono text-xs overflow-y-auto space-y-1.5 text-slate-300">
          {logs.length === 0 ? (
            <p className="text-slate-600">Awaiting target run...</p>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} className="leading-relaxed">
                <span className="text-slate-600 select-none mr-3">{String(idx + 1).padStart(2, '0')}</span>
                {log}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
