import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShieldAlert,
  AlertTriangle,
  FileText,
  Zap,
  CheckCircle,
  CheckCircle2,
  Info,
  Activity,
  ChevronDown,
  ChevronRight,
  RotateCw,
  ExternalLink,
  Layers,
  Clock,
  ShieldCheck,
  FileDiff,
  Printer,
  Download,
  Loader2
} from 'lucide-react';
import { apiClient } from '../config';

export default function CommitAudit() {
  const { repositoryId, scanId } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retrying, setRetrying] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState('');
  const [pdfSuccess, setPdfSuccess] = useState('');
  const [expandedFiles, setExpandedFiles] = useState<Record<string, boolean>>({});
  const [activeFindingsTab, setActiveFindingsTab] = useState<'ACTIONABLE' | 'FIXTURES'>('ACTIONABLE');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('ALL');
  const [selectedSeverityFilter, setSelectedSeverityFilter] = useState<string>('ALL');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('ALL');
  const [selectedClassificationFilter, setSelectedClassificationFilter] = useState<string>('ALL');

  const pollIntervalRef = useRef<number | null>(null);

  const handleDownloadPdf = async () => {
    if (!repositoryId || !scanId || downloadingPdf) return;
    setDownloadingPdf(true);
    setPdfError('');
    setPdfSuccess('');
    try {
      const res = await apiClient.get(`/repositories/${repositoryId}/scans/${scanId}/report.pdf`, {
        responseType: 'blob',
      });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const shortSha = data?.commit_sha ? data.commit_sha.substring(0, 7) : scanId;
      link.setAttribute('download', `gitflow-security-report-scan-${scanId}-${shortSha}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setPdfSuccess('PDF report generated and downloaded successfully.');
    } catch (err: any) {
      console.error('Failed to download PDF report', err);
      setPdfError(err.response?.data?.detail || 'Failed to generate PDF report. Please try again.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const fetchData = async (silent = false) => {
    if (!repositoryId || !scanId) {
      setLoading(false);
      return;
    }
    if (!silent) setLoading(true);
    try {
      const res = await apiClient.get(`/repositories/${repositoryId}/scans/${scanId}`);
      setData(res.data);
      setError('');
      return res.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load audit data');
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Polling setup if scan is QUEUED or RUNNING
    let isCancelled = false;
    let inFlight = false;

    const startPolling = () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = window.setInterval(async () => {
        if (inFlight || isCancelled) return;
        inFlight = true;
        try {
          const res = await apiClient.get(`/repositories/${repositoryId}/scans/${scanId}`);
          if (!isCancelled) {
            setData(res.data);
            if (res.data.status !== 'QUEUED' && res.data.status !== 'RUNNING') {
              if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
              }
            }
          }
        } catch (e) {
          console.error('Polling error', e);
        } finally {
          inFlight = false;
        }
      }, 2500);
    };

    if (data?.status === 'QUEUED' || data?.status === 'RUNNING') {
      startPolling();
    }

    return () => {
      isCancelled = true;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [repositoryId, scanId, data?.status]);

  const handleRetryScan = async () => {
    if (!repositoryId || !data?.commit_sha) return;
    setRetrying(true);
    try {
      await apiClient.post(`/repositories/${repositoryId}/scan`, { commit_sha: data.commit_sha });
      await fetchData(true);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to retry scan');
    } finally {
      setRetrying(false);
    }
  };

  const toggleFile = (filePath: string) => {
    setExpandedFiles(prev => ({ ...prev, [filePath]: !prev[filePath] }));
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-500 flex flex-col items-center justify-center">
        <Activity className="w-10 h-10 animate-spin text-brand-500 mb-4" />
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">Loading commit audit...</h2>
        <p className="text-sm text-slate-500 mt-1">Retrieving verified scanner findings and diffs</p>
      </div>
    );
  }

  if (!repositoryId || !scanId) return null;
  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-8 my-8 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/30 rounded-xl text-center">
        <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-red-700 dark:text-red-400 mb-2">Error Loading Audit</h3>
        <p className="text-slate-700 dark:text-slate-300 text-sm mb-4">{error}</p>
        <Link to="/" className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800">
          Return to Dashboard
        </Link>
      </div>
    );
  }
  if (!data) return <div className="p-8 text-center text-slate-500">No data found.</div>;

  const isPending = data.status === 'QUEUED' || data.status === 'RUNNING';
  const isFailed = data.status === 'FAILED';
  const isPartial = data.status === 'PARTIAL';

  const currentScore = data.risk_score;
  const prevCommit = data.previous_commit;
  const allFindings = data.findings || [];

  const actionableFindings = allFindings.filter(
    (f: any) => !f.is_test_fixture && f.classification !== 'Intentional test fixture or demonstration example'
  );
  const fixtureFindings = allFindings.filter(
    (f: any) => f.is_test_fixture || f.classification === 'Intentional test fixture or demonstration example'
  );

  const currentTabFindings = activeFindingsTab === 'ACTIONABLE' ? actionableFindings : fixtureFindings;

  // Filtered findings based on active tab and filters
  const filteredFindings = currentTabFindings.filter((f: any) => {
    if (selectedStatusFilter !== 'ALL' && f.status !== selectedStatusFilter) return false;
    if (selectedSeverityFilter !== 'ALL' && f.severity !== selectedSeverityFilter) return false;
    if (selectedCategoryFilter !== 'ALL' && f.category?.toLowerCase() !== selectedCategoryFilter.toLowerCase()) return false;
    if (selectedClassificationFilter === 'CONFIRMED' && f.classification !== 'Confirmed vulnerability or exposure') return false;
    if (selectedClassificationFilter === 'HEURISTIC' && f.classification !== 'Valid heuristic finding requiring manual verification') return false;
    if (selectedClassificationFilter === 'FIXTURE' && f.classification !== 'Intentional test fixture or demonstration example') return false;
    return true;
  });

  const baselineFindings = allFindings.filter((f: any) => f.status === 'BASELINE');
  const newFindings = allFindings.filter((f: any) => f.status === 'NEW');
  const unchangedFindings = allFindings.filter((f: any) => f.status === 'UNCHANGED');
  const resolvedFindings = allFindings.filter((f: any) => f.status === 'RESOLVED');

  const coverage = data.coverage || {};
  const tools = coverage.tools || {};

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row gap-6 items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center justify-between mb-4">
            <Link to="/" className="text-sm text-brand-500 hover:underline inline-block font-medium">
              &larr; Back to Dashboard
            </Link>
            <div className="flex items-center space-x-2 print:hidden">
              <button
                onClick={handleDownloadPdf}
                disabled={downloadingPdf}
                className="px-3.5 py-1.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors shadow-sm"
                title="Download verified server-generated PDF security report"
              >
                {downloadingPdf ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Generating PDF...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5" />
                    <span>Download PDF Report</span>
                  </>
                )}
              </button>
              <button
                onClick={() => window.print()}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors border border-slate-200 dark:border-slate-700"
                title="Open browser print dialog"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print View</span>
              </button>
            </div>
          </div>
          {pdfError && (
            <div className="mb-3 p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-xl flex items-center justify-between print:hidden">
              <span>{pdfError}</span>
              <button onClick={() => setPdfError('')} className="underline text-red-300">Dismiss</button>
            </div>
          )}
          {pdfSuccess && (
            <div className="mb-3 p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl flex items-center justify-between print:hidden">
              <span>{pdfSuccess}</span>
              <button onClick={() => setPdfSuccess('')} className="underline text-emerald-300">Dismiss</button>
            </div>
          )}
          <div className="flex items-center space-x-3 mb-2 flex-wrap">
            <h1 className="text-3xl font-bold font-mono">
              Commit {data.commit_sha ? data.commit_sha.substring(0, 7) : scanId}
            </h1>
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold border ${
                data.status === 'COMPLETED'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800'
                  : data.status === 'PARTIAL'
                  ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800'
                  : data.status === 'RUNNING'
                  ? 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800 animate-pulse'
                  : data.status === 'QUEUED'
                  ? 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/20 dark:text-purple-400 dark:border-purple-800'
                  : 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800'
              }`}
            >
              {data.status}
            </span>
            {isPartial && (
              <span className="px-2.5 py-0.5 rounded text-[11px] font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                Partial Coverage
              </span>
            )}
          </div>
          <p className="text-slate-800 dark:text-slate-200 text-lg font-medium">
            "{data.message || 'No commit message'}"
          </p>
          <div className="text-sm text-slate-600 dark:text-slate-400 mt-2 flex items-center space-x-2">
            <span>{data.author || 'Unknown'}</span>
            <span>&bull;</span>
            <span>{data.timestamp ? new Date(data.timestamp).toLocaleString() : 'Unknown time'}</span>
          </div>
        </div>

        {/* SECURITY SCORE CARD */}
        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft flex items-center justify-between min-w-[300px]">
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center">
              <ShieldCheck className="w-3.5 h-3.5 mr-1 text-brand-500" />
              Security Score
            </div>
            <div className="flex items-end space-x-3">
              <span className="text-4xl font-bold text-slate-900 dark:text-white leading-none">
                {currentScore !== null && currentScore !== undefined ? currentScore : isPending ? '--' : 'N/A'}
              </span>
              {prevCommit && data.score_delta !== null && (
                <span
                  className={`flex items-center px-2 py-0.5 rounded text-sm font-bold ${
                    data.score_delta > 0
                      ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                      : data.score_delta < 0
                      ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                      : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                  }`}
                >
                  {data.score_delta > 0 ? '+' : ''}
                  {data.score_delta}
                </span>
              )}
            </div>
            {prevCommit ? (
              <div className="text-xs text-slate-500 mt-2">
                Previous ({prevCommit.short_sha}):{' '}
                <span className="font-semibold text-slate-700 dark:text-slate-300">{prevCommit.score}</span>
              </div>
            ) : (
              <div className="text-xs text-brand-600 dark:text-brand-400 mt-2 font-semibold">BASELINE SCAN</div>
            )}
            {currentScore === 100 && (
              <div className="text-[11px] text-slate-500 mt-2 max-w-[220px] leading-tight">
                No confirmed issues were detected by the checks that completed.
              </div>
            )}
          </div>

          <div className="flex flex-col space-y-1.5 text-right border-l border-border-light dark:border-border-dark pl-4 text-xs font-medium">
            <div>
              <span className="text-red-500 font-bold">{newFindings.length}</span>{' '}
              <span className="text-slate-500">New</span>
            </div>
            <div>
              <span className="text-emerald-500 font-bold">{resolvedFindings.length}</span>{' '}
              <span className="text-slate-500">Resolved</span>
            </div>
            <div>
              <span className="text-slate-500 font-bold">{baselineFindings.length}</span>{' '}
              <span className="text-slate-500">Baseline</span>
            </div>
            <div>
              <span className="text-slate-400 font-bold">{unchangedFindings.length}</span>{' '}
              <span className="text-slate-400">Unchanged</span>
            </div>
          </div>
        </div>
      </div>

      {/* SCANNER COVERAGE WARNING BANNER */}
      {isPartial && (
        <div className="p-4 rounded-xl border border-amber-300 dark:border-amber-900/60 bg-amber-50/80 dark:bg-amber-950/30 flex items-start space-x-3 text-amber-900 dark:text-amber-200">
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs leading-relaxed">
            <span className="font-bold">Scanner Coverage Notice:</span> One or more security analyzers could not run to completion. Findings and risk score represent only the completed tools. Review tool coverage diagnostics below.
          </div>
        </div>
      )}

      {/* PENDING / RUNNING BANNER */}
      {isPending && (
        <div className="p-6 rounded-xl border border-blue-200 dark:border-blue-900/40 bg-blue-50/60 dark:bg-blue-900/20 flex items-start space-x-4">
          <Activity className="w-6 h-6 text-blue-600 dark:text-blue-400 animate-spin mt-1 shrink-0" />
          <div className="flex-1">
            <h3 className="font-bold text-blue-900 dark:text-blue-200 text-base">
              Scan #{data.id} is {data.status}
            </h3>
            <p className="text-sm text-blue-800 dark:text-blue-300 mt-1">
              Deterministic security scanners (SAST, Secret Scanning, Dependency Advisories, License Compliance) are actively analyzing this commit.
              This report refreshes automatically upon completion.
            </p>
          </div>
        </div>
      )}

      {/* FAILED BANNER WITH RETRY */}
      {isFailed && (
        <div className="p-6 rounded-xl border border-red-200 dark:border-red-900/40 bg-red-50/80 dark:bg-red-900/20 flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
            <div>
              <h3 className="font-bold text-red-900 dark:text-red-200 text-base">Scan Execution Failed</h3>
              <p className="text-sm text-red-800 dark:text-red-300 mt-1">
                {data.error_message || 'An error occurred during repository analysis.'}
              </p>
            </div>
          </div>
          <button
            onClick={handleRetryScan}
            disabled={retrying}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-semibold flex items-center space-x-2 transition-colors disabled:opacity-50"
          >
            <RotateCw className={`w-4 h-4 ${retrying ? 'animate-spin' : ''}`} />
            <span>{retrying ? 'Retrying...' : 'Retry Scan'}</span>
          </button>
        </div>
      )}

      {/* COMMIT SUMMARY */}
      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center">
          <Activity className="w-4 h-4 mr-2 text-brand-500" />
          Evidence-Based Commit Summary
        </h2>
        <div className="text-slate-800 dark:text-slate-200 whitespace-pre-line leading-relaxed text-sm">
          {data.human_summary || 'No summary available.'}
        </div>
      </div>

      {/* SCANNER COVERAGE PANEL */}
      {coverage && coverage.tools && Object.keys(tools).length > 0 && (
        <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
          <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center">
            <Layers className="w-4 h-4 mr-2 text-brand-500" />
            Scanner Coverage & Diagnostics
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {Object.entries(tools).map(([key, t]: [string, any]) => (
              <div
                key={key}
                className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold uppercase text-slate-600 dark:text-slate-400">{key}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      t.status === 'COMPLETED'
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                        : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                    }`}
                  >
                    {t.status}
                  </span>
                </div>
                <div className="text-xs text-slate-700 dark:text-slate-300 truncate" title={t.tool_name}>
                  {t.tool_name}
                </div>
                <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
                  <span>{t.files_scanned} files</span>
                  <span className="flex items-center">
                    <Clock className="w-3 h-3 mr-0.5 inline" />
                    {t.duration_seconds}s
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500 flex-wrap gap-2">
            <div>
              Examined <span className="font-semibold text-slate-700 dark:text-slate-300">{coverage.files_examined}</span> files &bull; Languages:{' '}
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                {coverage.supported_languages?.join(', ') || 'Auto-detected'}
              </span>
            </div>
            <div>
              Total Scan Time:{' '}
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                {coverage.total_duration_seconds}s
              </span>
            </div>
          </div>
        </div>
      )}

      {/* WHAT CHANGED & SCORE EXPLANATION */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* WHAT CHANGED */}
        <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
          <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center">
            <FileText className="w-4 h-4 mr-2 text-brand-500" />
            What Changed ({data.changes?.length || 0} Files)
          </h2>
          <div className="space-y-3 max-h-80 overflow-y-auto pr-1 custom-scrollbar">
            {data.changes?.length > 0 ? (
              data.changes.map((c: any, i: number) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800"
                >
                  <div className="flex items-center truncate mr-4">
                    <span
                      className={`w-2 h-2 rounded-full mr-3 shrink-0 ${
                        c.status === 'A' || c.status === 'added'
                          ? 'bg-emerald-500'
                          : c.status === 'D' || c.status === 'deleted'
                          ? 'bg-red-500'
                          : c.status.startsWith('R') || c.status === 'renamed'
                          ? 'bg-amber-500'
                          : 'bg-brand-500'
                      }`}
                    />
                    <div className="truncate">
                      <span className="font-mono text-sm text-slate-800 dark:text-slate-200 truncate block" title={c.file}>
                        {c.file}
                      </span>
                      {c.old_path && (
                        <span className="text-[11px] text-slate-400 block">Renamed from {c.old_path}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-3 text-xs font-mono shrink-0">
                    {c.is_binary ? (
                      <span className="text-slate-400 text-[11px]">binary</span>
                    ) : (
                      <>
                        <span className="text-emerald-600 dark:text-emerald-400">+{c.additions}</span>
                        <span className="text-red-600 dark:text-red-400">-{c.deletions}</span>
                      </>
                    )}
                  </div>
                </div>
              ))
            ) : isPending ? (
              <p className="text-sm text-slate-500 italic">Analyzing commit changes...</p>
            ) : (
              <p className="text-sm text-slate-500">No file changes recorded for this commit.</p>
            )}
          </div>
        </div>

        {/* WHY THE SCORE CHANGED & ACTIONS */}
        <div className="space-y-6">
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center">
              <Zap className="w-4 h-4 mr-2 text-brand-500" />
              Score Explanation
            </h2>
            <p className="text-slate-800 dark:text-slate-200 text-sm leading-relaxed">
              {data.score_explanation || 'No explanation provided.'}
            </p>
          </div>

          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center">
              <CheckCircle className="w-4 h-4 mr-2 text-brand-500" />
              Actions Detected
            </h2>
            {data.actions_detected && data.actions_detected.length > 0 ? (
              <ul className="space-y-2">
                {data.actions_detected.map((action: string, i: number) => (
                  <li key={i} className="flex items-start text-sm text-slate-800 dark:text-slate-200">
                    <span className="text-brand-500 mr-2 mt-0.5 font-bold">+</span> {action}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No security-critical structural actions detected.</p>
            )}
          </div>
        </div>
      </div>

      {/* SECURITY FINDINGS SECTION */}
      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
        {/* TABS: Actionable Vulnerabilities vs Test Fixtures Audit Trail */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between pb-4 border-b border-border-light dark:border-border-dark mb-6 gap-4">
          <div className="flex items-center space-x-2 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl overflow-x-auto">
            <button
              onClick={() => {
                setActiveFindingsTab('ACTIONABLE');
                setSelectedClassificationFilter('ALL');
              }}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-2 shrink-0 ${
                activeFindingsTab === 'ACTIONABLE'
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <ShieldAlert className="w-4 h-4 text-brand-500" />
              <span>Actionable Vulnerabilities</span>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
                  actionableFindings.length === 0
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                    : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
                }`}
              >
                {actionableFindings.length === 0 ? '0 (Clean)' : actionableFindings.length}
              </span>
            </button>

            <button
              onClick={() => {
                setActiveFindingsTab('FIXTURES');
                setSelectedClassificationFilter('ALL');
              }}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-2 shrink-0 ${
                activeFindingsTab === 'FIXTURES'
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Layers className="w-4 h-4 text-blue-500" />
              <span>Test & Benchmark Fixtures Audit Trail</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                {fixtureFindings.length} (0 Deduction)
              </span>
            </button>
          </div>

          {/* FILTER CONTROLS */}
          <div className="flex items-center space-x-2 flex-wrap gap-2 text-xs">
            {/* Status Filter */}
            <div className="flex bg-slate-100 dark:bg-slate-800 p-0.5 rounded-lg">
              {['ALL', 'NEW', 'RESOLVED', 'BASELINE', 'UNCHANGED'].map(st => (
                <button
                  key={st}
                  onClick={() => setSelectedStatusFilter(st)}
                  className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                    selectedStatusFilter === st
                      ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            {/* Severity Filter */}
            <select
              value={selectedSeverityFilter}
              onChange={e => setSelectedSeverityFilter(e.target.value)}
              className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg px-2 py-1 text-xs font-medium border-0 focus:ring-1 focus:ring-brand-500"
            >
              <option value="ALL">All Severities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>

            {/* Category Filter */}
            <select
              value={selectedCategoryFilter}
              onChange={e => setSelectedCategoryFilter(e.target.value)}
              className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg px-2 py-1 text-xs font-medium border-0 focus:ring-1 focus:ring-brand-500"
            >
              <option value="ALL">All Categories</option>
              <option value="Vulnerability">SAST Vulnerability</option>
              <option value="Secret">Secret</option>
              <option value="Dependency">Dependency</option>
              <option value="License">License</option>
              <option value="Quality">Code Quality</option>
            </select>
          </div>
        </div>

        {/* Informational Callout for Fixtures Tab */}
        {activeFindingsTab === 'FIXTURES' && (
          <div className="p-4 rounded-xl border border-blue-500/20 bg-blue-500/5 dark:bg-blue-950/20 mb-6 flex items-start space-x-3 text-xs text-slate-600 dark:text-slate-400">
            <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-900 dark:text-white mb-1">
                Audit Trail — Isolated Test & Benchmark Fixtures ({fixtureFindings.length})
              </p>
              <p className="leading-relaxed">
                These findings are located inside isolated test directories, unit test suites, or the scanner benchmark engine (e.g., <code>backend/app/benchmarks/benchmark_engine.py</code> and <code>backend/tests/fixtures/</code>). They are intentional test assertions and demonstration vectors used to benchmark scanner sensitivity. Because they are strictly isolated from production code, they do <strong>not</strong> pose an active risk and incur <strong>0 score deduction</strong>.
              </p>
            </div>
          </div>
        )}

        {/* Clean Banner when 0 Actionable Findings */}
        {activeFindingsTab === 'ACTIONABLE' && actionableFindings.length === 0 ? (
          <div className="p-10 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 dark:bg-emerald-950/20 text-center my-4">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center mx-auto mb-4 border border-emerald-500/20 shadow-sm">
              <CheckCircle2 className="w-9 h-9" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
              Zero Actionable Security Exposures Detected
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 max-w-xl mx-auto mb-5 leading-relaxed">
              Deterministic SAST, Secret, Dependency, License, and Quality analyzers evaluated all production code and confirmed zero security vulnerabilities. Current Security Score: <span className="font-bold text-emerald-600 dark:text-emerald-400">{currentScore ?? 100}/100</span>.
            </p>
            {fixtureFindings.length > 0 && (
              <button
                onClick={() => setActiveFindingsTab('FIXTURES')}
                className="px-4 py-2 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold rounded-lg inline-flex items-center space-x-2 transition-colors border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-750 shadow-xs"
              >
                <span>Inspect {fixtureFindings.length} Isolated Test & Benchmark Fixtures (0 Score Deduction)</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        ) : (
          /* FINDINGS LIST */
          <div className="space-y-4">
            {filteredFindings.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                {isPending
                  ? 'Scan is processing. Findings will appear once complete.'
                  : 'No issues match the selected filters.'}
              </div>
            ) : (
              filteredFindings.map((f: any, idx: number) => {
                const isResolved = f.status === 'RESOLVED';
                const isFixture = f.is_test_fixture || f.classification === 'Intentional test fixture or demonstration example';
                return (
                  <div
                    key={idx}
                    className={`p-5 rounded-xl border transition-all ${
                      isResolved
                        ? 'bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/40 opacity-80'
                        : isFixture
                        ? 'bg-slate-50/50 dark:bg-slate-850/30 border-blue-200/60 dark:border-blue-900/40'
                        : f.severity === 'Critical'
                        ? 'bg-red-50/40 dark:bg-red-950/20 border-red-200 dark:border-red-900/40'
                        : f.severity === 'High'
                        ? 'bg-amber-50/40 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/40'
                        : 'bg-slate-50/60 dark:bg-slate-850/40 border-slate-200 dark:border-slate-700/60'
                    }`}
                  >
                    <div className="flex items-start justify-between flex-wrap gap-2 mb-2">
                      <div className="flex items-center space-x-2 flex-wrap">
                        {isFixture ? (
                          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                            Test Fixture (0 Deduction)
                          </span>
                        ) : (
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-bold ${
                              f.severity === 'Critical'
                                ? 'bg-red-600 text-white'
                                : f.severity === 'High'
                                ? 'bg-amber-500 text-white'
                                : f.severity === 'Medium'
                                ? 'bg-yellow-500 text-slate-900'
                                : 'bg-slate-500 text-white'
                            }`}
                          >
                            {f.severity}
                          </span>
                        )}

                        <span
                          className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                            f.status === 'NEW'
                              ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                              : f.status === 'RESOLVED'
                              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 line-through'
                              : f.status === 'BASELINE'
                              ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
                              : 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                          }`}
                        >
                          {f.status}
                        </span>

                        <span className="text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-slate-600 dark:text-slate-400">
                          {f.rule_id || f.category}
                        </span>

                        {f.classification && (
                          <span
                            className={`text-[11px] px-2 py-0.5 rounded font-semibold ${
                              isFixture
                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                                : f.classification === 'Confirmed vulnerability or exposure'
                                ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                                : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                            }`}
                          >
                            {isFixture
                              ? 'Test Fixture / Sample'
                              : f.classification === 'Confirmed vulnerability or exposure'
                              ? 'Confirmed Issue'
                              : 'Heuristic Review'}
                          </span>
                        )}

                        {f.confidence && (
                          <span className="text-[11px] text-slate-500">Confidence: {f.confidence}</span>
                        )}
                      </div>

                      <div className="font-mono text-xs text-slate-600 dark:text-slate-400">
                        {f.file_path}
                        {f.line_number ? `:${f.line_number}` : ''}
                      </div>
                    </div>

                    <h3
                      className={`text-base font-bold text-slate-900 dark:text-white mb-2 ${
                        isResolved ? 'line-through text-slate-500 dark:text-slate-400' : ''
                      }`}
                    >
                      {f.title || f.category}
                    </h3>

                    <p className="text-sm text-slate-700 dark:text-slate-300 mb-3">{f.description}</p>

                    {/* Code snippet */}
                    {f.code_snippet && (
                      <div className="mb-3 bg-slate-900 rounded-lg p-3 overflow-x-auto text-xs font-mono text-slate-200">
                        <code>{f.code_snippet}</code>
                      </div>
                    )}

                    {/* Evidence & Remediation */}
                    {(f.evidence || f.remediation || f.classification) && (
                      <div className="mt-3 pt-3 border-t border-slate-200/60 dark:border-slate-800 text-xs space-y-1.5">
                        {f.classification && (
                          <div>
                            <strong className="text-slate-700 dark:text-slate-300">Classification:</strong>{' '}
                            <span className="text-slate-600 dark:text-slate-400">{f.classification}</span>
                          </div>
                        )}
                        {f.evidence && (
                          <div>
                            <strong className="text-slate-700 dark:text-slate-300">Evidence:</strong>{' '}
                            <span className="text-slate-600 dark:text-slate-400">{f.evidence}</span>
                          </div>
                        )}
                        {f.impact && (
                          <div>
                            <strong className="text-slate-700 dark:text-slate-300">Impact:</strong>{' '}
                            <span className="text-slate-600 dark:text-slate-400">{f.impact}</span>
                          </div>
                        )}
                        {f.remediation && (
                          <div className="text-brand-600 dark:text-brand-400">
                            <strong>Remediation:</strong> <span>{f.remediation}</span>
                          </div>
                        )}
                      </div>
                    )}

                    {f.references && f.references.length > 0 && (
                      <div className="mt-2 flex items-center space-x-3 text-[11px] text-brand-500">
                        {f.references.map((refUrl: string, rIdx: number) => (
                          <a
                            key={rIdx}
                            href={refUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="hover:underline flex items-center"
                          >
                            Advisory Reference <ExternalLink className="w-3 h-3 ml-1" />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* DIFF VIEWER (WHAT CHANGED INSIDE FILES) */}
      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-6 flex items-center">
          <FileDiff className="w-4 h-4 mr-2 text-brand-500" />
          Verified Git Patch & Code Diff Viewer
        </h2>

        <div className="space-y-4">
          {data.changes?.length > 0 ? (
            data.changes.map((c: any, i: number) => {
              const fileActionable = allFindings.filter((f: any) => f.file_path === c.file && !f.is_test_fixture && f.classification !== 'Intentional test fixture or demonstration example');
              const fileFixtures = allFindings.filter((f: any) => f.file_path === c.file && (f.is_test_fixture || f.classification === 'Intentional test fixture or demonstration example'));
              const hasActionable = fileActionable.length > 0;
              const hasFixtures = fileFixtures.length > 0;
              const isExpanded = expandedFiles[c.file];

              return (
                <div key={i} className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
                  <div
                    className={`flex items-center justify-between p-3.5 cursor-pointer select-none transition-colors ${
                      hasActionable
                        ? 'bg-red-50/60 dark:bg-red-950/20 hover:bg-red-50 dark:hover:bg-red-950/40'
                        : hasFixtures
                        ? 'bg-blue-50/40 dark:bg-blue-950/20 hover:bg-blue-50 dark:hover:bg-blue-950/40'
                        : 'bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                    onClick={() => toggleFile(c.file)}
                  >
                    <div className="flex items-center space-x-3 truncate">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
                      )}
                      <span className="font-mono text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                        {c.file}
                      </span>
                      {c.old_path && (
                        <span className="text-xs text-slate-400">({c.old_path} &rarr; {c.file})</span>
                      )}
                      {hasActionable && (
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300">
                          {fileActionable.length} vulnerability
                        </span>
                      )}
                      {hasFixtures && (
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300">
                          {fileFixtures.length} fixture sample(s)
                        </span>
                      )}
                    </div>
                    <div className="flex items-center space-x-4 text-xs font-mono shrink-0">
                      {c.is_binary ? (
                        <span className="text-slate-400 font-sans">binary</span>
                      ) : (
                        <>
                          <span className="text-emerald-600 dark:text-emerald-400">+{c.additions}</span>
                          <span className="text-red-600 dark:text-red-400">-{c.deletions}</span>
                        </>
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="border-t border-slate-200 dark:border-slate-700 bg-background-light dark:bg-background-dark">
                      {/* File actionable findings notice */}
                      {hasActionable && (
                        <div className="p-4 bg-red-50/80 dark:bg-red-900/10 border-b border-red-100 dark:border-red-900/30 space-y-2">
                          <h4 className="text-xs font-bold uppercase text-red-800 dark:text-red-300">
                            Actionable Security Findings on this file:
                          </h4>
                          {fileActionable.map((f: any, idx: number) => (
                            <div key={idx} className="text-xs flex items-center justify-between">
                              <span className="font-semibold text-red-700 dark:text-red-400">
                                {f.severity} - {f.title}
                              </span>
                              <span className="text-slate-500 font-mono">
                                {f.line_number ? `Line ${f.line_number}` : 'File'}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* File test fixtures notice */}
                      {hasFixtures && (
                        <div className="p-4 bg-blue-50/60 dark:bg-blue-900/10 border-b border-blue-100 dark:border-blue-900/30 space-y-2">
                          <h4 className="text-xs font-bold uppercase text-blue-800 dark:text-blue-300">
                            Isolated Test & Benchmark Fixtures (0 Score Deduction):
                          </h4>
                          {fileFixtures.map((f: any, idx: number) => (
                            <div key={idx} className="text-xs flex items-center justify-between">
                              <span className="font-semibold text-blue-700 dark:text-blue-400">
                                Test Sample: {f.title}
                              </span>
                              <span className="text-slate-500 font-mono">
                                {f.line_number ? `Line ${f.line_number}` : 'File'}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Raw unified diff */}
                      {c.patch ? (
                        <div className="overflow-x-auto p-4 custom-scrollbar bg-slate-950">
                          <pre className="text-xs font-mono leading-relaxed">
                            {c.patch.split('\n').map((line: string, lIdx: number) => {
                              let lineClass = 'px-2 py-0.5 block ';
                              if (line.startsWith('+') && !line.startsWith('+++')) {
                                lineClass += 'bg-emerald-950/60 text-emerald-300';
                              } else if (line.startsWith('-') && !line.startsWith('---')) {
                                lineClass += 'bg-red-950/60 text-red-300';
                              } else if (line.startsWith('@@')) {
                                lineClass += 'bg-slate-800/80 text-blue-300 font-bold';
                              } else {
                                lineClass += 'text-slate-400';
                              }

                              return (
                                <span key={lIdx} className={lineClass}>
                                  {line}
                                </span>
                              );
                            })}
                          </pre>
                        </div>
                      ) : (
                        <div className="p-6 text-center text-sm text-slate-500 italic">
                          {c.is_binary ? 'Binary file change. Diffs are not displayed.' : 'No patch content available.'}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <p className="text-sm text-slate-500 italic">No file diffs recorded for this commit.</p>
          )}
        </div>
      </div>
    </div>
  );
}
