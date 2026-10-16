import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitCommit, CheckCircle2, Activity, AlertCircle, Loader2, RefreshCw, ExternalLink, X, Trash2, Compass } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiClient } from '../config';
import { ScanningHUD } from '../components/ScanningHUD';

interface ScanNotification {
  type: 'info' | 'success' | 'error';
  message: string;
  scanId?: number;
  repoId?: number;
  sha?: string;
  score?: number | null;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [repos, setRepos] = useState<any[]>([]);
  const [activeRepoId, setActiveRepoId] = useState<string | null>(localStorage.getItem('gitflow_active_repo') || null);
  const [history, setHistory] = useState<{ scanId: number; findingsCount: number; repoId: string; commit: string; score: number | null; date: string; scoreDelta: number | null; alerts?: string[] }[]>([]);
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [repoError, setRepoError] = useState('');
  const [scanningRepoId, setScanningRepoId] = useState<number | null>(null);
  const [scanNotification, setScanNotification] = useState<ScanNotification | null>(null);

  // Scanning HUD Modal State
  const [hudOpen, setHudOpen] = useState(false);
  const [hudRepo, setHudRepo] = useState<any | null>(null);
  const [hudScanId, setHudScanId] = useState<number | string | null>(null);
  const [hudCommitSha, setHudCommitSha] = useState<string>('HEAD');
  const [hudStatus, setHudStatus] = useState<string | null>(null);
  const [hudScore, setHudScore] = useState<number | null>(null);
  const [hudActionableCount, setHudActionableCount] = useState<number>(0);
  const [hudFixturesCount, setHudFixturesCount] = useState<number>(0);
  const [hudError, setHudError] = useState<string | null>(null);

  // Safe repository removal dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [repoToDelete, setRepoToDelete] = useState<any | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [deleteSuccessMsg, setDeleteSuccessMsg] = useState('');

  const activeRepoIdRef = useRef(activeRepoId);
  const historyLoadedRef = useRef(false);
  const pollTimerRef = useRef<number | null>(null);

  const handleRepoChange = (e: any) => {
    const newId = e.target.value;
    activeRepoIdRef.current = newId;
    historyLoadedRef.current = false;
    setActiveRepoId(newId);
    localStorage.setItem('gitflow_active_repo', newId);
  };

  const fetchRepos = useCallback(async (silent = false) => {
    try {
      const reposRes = await apiClient.get('/repositories/');
      setRepoError('');
      setRepos(reposRes.data);
      
      if (reposRes.data.length === 0) {
        if (!silent) setLoading(false);
        return;
      }
      
      let targetId = activeRepoIdRef.current;
      if (!targetId || !reposRes.data.find((r: any) => r.id.toString() === targetId)) {
        targetId = reposRes.data[0].id.toString();
        activeRepoIdRef.current = targetId;
        setActiveRepoId(targetId);
        localStorage.setItem('gitflow_active_repo', targetId as string);
      }
    } catch (err) {
      console.error('Failed to fetch repos', err);
      if (!silent) setRepoError('Could not load repositories. Check your connection and try again.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  const fetchHistory = useCallback(async (repoId: string, silent = false) => {
    if (!silent && !historyLoadedRef.current) setHistoryLoading(true);
    try {
      const historyRes = await apiClient.get(`/repositories/${repoId}/risk-history`);
      const latestHistory = historyRes.data.slice(-50);
      const chartData = latestHistory.map((h: any) => ({
        scanId: h.id,
        findingsCount: h.findings_count,
        repoId: repoId,
        commit: h.short_sha,
        score: h.risk_score,
        date: new Date(h.scanned_at).toLocaleDateString(),
        scoreDelta: h.score_delta,
        alerts: h.alerts
      }));
      setHistory(chartData);
    } catch (err) {
      console.error('Failed to fetch history', err);
    } finally {
      historyLoadedRef.current = true;
      if (!silent) setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRepos();
    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') fetchRepos(true);
    }, 30000);
    return () => window.clearInterval(interval);
  }, [fetchRepos]);

  useEffect(() => {
    if (!activeRepoId) return;
    fetchHistory(activeRepoId);
    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') fetchHistory(activeRepoId, true);
    }, 30000);
    return () => window.clearInterval(interval);
  }, [activeRepoId, fetchHistory]);

  // Clean up polling timer on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, []);

  // Close confirmation modal on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && deleteDialogOpen && !isDeleting) {
        setDeleteDialogOpen(false);
        setRepoToDelete(null);
        setDeleteError('');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [deleteDialogOpen, isDeleting]);

  const handleOpenDeleteDialog = (repo: any, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteError('');
    setRepoToDelete(repo);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!repoToDelete || isDeleting) return;
    setIsDeleting(true);
    setDeleteError('');

    try {
      await apiClient.delete(`/repositories/${repoToDelete.id}`);
      const deletedId = repoToDelete.id.toString();
      const deletedName = repoToDelete.name;

      // Immediately update local repos state without full page reload
      const remainingRepos = repos.filter((r) => r.id !== repoToDelete.id);
      setRepos(remainingRepos);

      // If deleted repository was active, automatically pick next or clear
      if (activeRepoId === deletedId) {
        if (remainingRepos.length > 0) {
          const nextRepoId = remainingRepos[0].id.toString();
          activeRepoIdRef.current = nextRepoId;
          setActiveRepoId(nextRepoId);
          localStorage.setItem('gitflow_active_repo', nextRepoId);
          fetchHistory(nextRepoId, false);
        } else {
          activeRepoIdRef.current = null;
          setActiveRepoId(null);
          localStorage.removeItem('gitflow_active_repo');
          setHistory([]);
        }
      }

      setDeleteDialogOpen(false);
      setRepoToDelete(null);
      setDeleteSuccessMsg(`Repository "${deletedName}" was successfully removed from Zylorun.`);

      setTimeout(() => {
        setDeleteSuccessMsg('');
      }, 6000);
    } catch (err: any) {
      console.error('Failed to remove repository', err);
      const msg = err.response?.data?.detail || 'Failed to remove repository. Please try again.';
      setDeleteError(msg);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleManualScan = async (repo: any, e: React.MouseEvent) => {
    e.stopPropagation();
    if (scanningRepoId !== null) return;

    setScanningRepoId(repo.id);
    setHudRepo(repo);
    setHudCommitSha('HEAD');
    setHudScanId(null);
    setHudStatus('RUNNING');
    setHudScore(null);
    setHudError(null);
    setHudActionableCount(0);
    setHudFixturesCount(0);
    setHudOpen(true);

    setScanNotification({
      type: 'info',
      message: `Triggering scan for repository "${repo.name}" at HEAD...`,
      repoId: repo.id
    });

    try {
      const res = await apiClient.post(`/repositories/${repo.id}/scan`, { commit_sha: 'HEAD' });
      const { scan_id, status, commit_sha, message } = res.data;
      setHudScanId(scan_id);
      if (commit_sha) setHudCommitSha(commit_sha);

      if (status === 'COMPLETED' || status === 'PARTIAL') {
        setScanningRepoId(null);
        setHudStatus(status);
        try {
          const auditRes = await apiClient.get(`/repositories/${repo.id}/scans/${scan_id}/audit`);
          const audit = auditRes.data;
          setHudScore(audit.risk_score);
          const actCount = (audit.findings || []).filter((f: any) => !f.is_test_fixture).length;
          const fixCount = (audit.findings || []).filter((f: any) => f.is_test_fixture).length;
          setHudActionableCount(actCount);
          setHudFixturesCount(fixCount);
        } catch {
          setHudScore(100);
        }

        setScanNotification({
          type: 'success',
          message: message || `Scan #${scan_id} completed successfully for commit ${commit_sha.substring(0, 7)}.`,
          scanId: scan_id,
          repoId: repo.id,
          sha: commit_sha
        });
        await fetchRepos(true);
        if (activeRepoId === repo.id.toString()) {
          await fetchHistory(repo.id.toString(), true);
        }
        return;
      }

      setScanNotification({
        type: 'info',
        message: message || `Scan #${scan_id} queued. Running deterministic security analysis...`,
        scanId: scan_id,
        repoId: repo.id,
        sha: commit_sha
      });

      // Poll scan endpoint until completion or failure
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      const startTime = Date.now();
      const maxWaitMs = 180000; // 3 minutes timeout

      pollTimerRef.current = window.setInterval(async () => {
        if (Date.now() - startTime > maxWaitMs) {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          setScanningRepoId(null);
          setHudStatus('TIMEOUT');
          setHudError(`Scan #${scan_id} is taking longer than usual. It continues to run in the background.`);
          setScanNotification({
            type: 'error',
            message: `Scan #${scan_id} is taking longer than usual. It continues to run in the background.`,
            scanId: scan_id,
            repoId: repo.id
          });
          return;
        }

        try {
          const pollRes = await apiClient.get(`/repositories/${repo.id}/scans/${scan_id}`);
          const scanData = pollRes.data;

          if (scanData.status === 'COMPLETED' || scanData.status === 'PARTIAL') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
            setScanningRepoId(null);
            setHudStatus('COMPLETED');
            setHudScore(scanData.risk_score);

            try {
              const auditRes = await apiClient.get(`/repositories/${repo.id}/scans/${scan_id}/audit`);
              const audit = auditRes.data;
              const actCount = (audit.findings || []).filter((f: any) => !f.is_test_fixture).length;
              const fixCount = (audit.findings || []).filter((f: any) => f.is_test_fixture).length;
              setHudActionableCount(actCount);
              setHudFixturesCount(fixCount);
            } catch {
              // fallback
            }

            setScanNotification({
              type: 'success',
              message: `Scan #${scan_id} finished! Security Score: ${scanData.risk_score !== null ? scanData.risk_score : 'Recorded'}/100.`,
              scanId: scan_id,
              repoId: repo.id,
              sha: scanData.commit_sha,
              score: scanData.risk_score
            });
            await fetchRepos(true);
            if (activeRepoId === repo.id.toString()) {
              await fetchHistory(repo.id.toString(), true);
            }
          } else if (scanData.status === 'FAILED') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
            setScanningRepoId(null);
            setHudStatus('FAILED');
            setHudError(scanData.error_message || 'Internal scan error');
            setScanNotification({
              type: 'error',
              message: `Scan #${scan_id} failed: ${scanData.error_message || 'Internal scan error'}.`,
              scanId: scan_id,
              repoId: repo.id
            });
            await fetchRepos(true);
          }
        } catch (pollErr) {
          console.error('Scan polling error', pollErr);
        }
      }, 1500);

    } catch (err: any) {
      console.error('Failed to trigger scan', err);
      setScanningRepoId(null);
      setHudStatus('FAILED');
      const detail = err.response?.data?.detail || 'Failed to initiate scan. Please check repository access.';
      setHudError(detail);
      setScanNotification({
        type: 'error',
        message: detail,
        repoId: repo.id
      });
    }
  };

  const stats = [
    { title: 'Total Repositories', value: repos.length, change: '', trend: 'neutral' },
    {
      title: 'Current Security Score',
      value: history.length > 0 ? (history[history.length - 1].score !== null ? `${history[history.length - 1].score}/100` : 'Unavailable') : 'NO COMPLETED SCAN',
      change: history.length > 0 ? (history[history.length - 1].scoreDelta === null ? 'Baseline scan' : `Latest delta: ${history[history.length - 1].scoreDelta! > 0 ? '+' : ''}${history[history.length - 1].scoreDelta}`) : 'Connect a repo',
      trend: 'neutral'
    },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex justify-between items-center mb-6 pt-6">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-slate-500 text-sm mt-1">Continuous security intelligence & commit risk passport</p>
        </div>
        <button
          onClick={() => navigate('/onboarding')}
          className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors shadow-sm font-medium"
        >
          + Add Repository
        </button>
      </div>

      {/* Repository Removal Success Notification */}
      {deleteSuccessMsg && (
        <div
          role="status"
          className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/80 dark:bg-emerald-950/30 text-emerald-900 dark:text-emerald-300 flex items-center justify-between shadow-sm animate-fade-in"
        >
          <div className="flex items-center space-x-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <p className="text-sm font-medium">{deleteSuccessMsg}</p>
          </div>
          <button
            onClick={() => setDeleteSuccessMsg('')}
            className="p-1 hover:opacity-75 rounded transition-opacity"
            aria-label="Dismiss message"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Real-time Scan Notification Banner */}
      {scanNotification && (
        <div className={`p-4 rounded-xl border flex items-center justify-between transition-all shadow-sm ${
          scanNotification.type === 'info'
            ? 'bg-blue-50/80 dark:bg-blue-950/30 border-blue-200 dark:border-blue-900/50 text-blue-900 dark:text-blue-300'
            : scanNotification.type === 'success'
            ? 'bg-emerald-50/80 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900/50 text-emerald-900 dark:text-emerald-300'
            : 'bg-red-50/80 dark:bg-red-950/30 border-red-200 dark:border-red-900/50 text-red-900 dark:text-red-300'
        }`}>
          <div className="flex items-center space-x-3">
            {scanNotification.type === 'info' && <Loader2 className="w-5 h-5 animate-spin text-blue-600 dark:text-blue-400 shrink-0" />}
            {scanNotification.type === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />}
            {scanNotification.type === 'error' && <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0" />}
            <div>
              <p className="font-medium text-sm">{scanNotification.message}</p>
              {scanNotification.sha && (
                <p className="text-xs opacity-75 font-mono mt-0.5">Commit: {scanNotification.sha.substring(0, 7)}</p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {scanNotification.scanId && scanNotification.repoId && (
              <button
                onClick={() => navigate(`/repositories/${scanNotification.repoId}/scans/${scanNotification.scanId}/audit`)}
                className="px-3 py-1.5 bg-white dark:bg-slate-800 text-xs font-semibold rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 flex items-center space-x-1.5 transition-colors"
              >
                <span>View Commit Audit</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            )}
            <button
              onClick={() => setScanNotification(null)}
              className="p-1 hover:opacity-75 rounded transition-opacity"
              aria-label="Dismiss banner"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {stats.map((stat, i) => (
          <div key={i} className="p-6 rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft dark:shadow-soft-dark">
            <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">{stat.title}</h3>
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-bold">{stat.value}</span>
              <span className="text-sm font-medium text-slate-500">{stat.change}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft dark:shadow-soft-dark overflow-hidden p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">Repository Risk History</h2>
          {history.length > 0 && (
            <span className="text-xs text-slate-500">{history.length} scans tracked</span>
          )}
        </div>
        <div className="h-72 w-full flex items-center justify-center text-slate-500">
          {historyLoading ? (
            <div className="animate-pulse w-full h-full flex flex-col justify-end space-y-2">
               <div className="h-full w-full bg-slate-200 dark:bg-slate-800 rounded opacity-50"></div>
            </div>
          ) : 
           history.length === 0 ? "No risk history yet. Push a commit or run your first scan to start tracking risk." :
           (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} vertical={false} />
                <XAxis dataKey="commit" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                  itemStyle={{ color: '#8b5cf6' }}
                />
                <Line type="monotone" dataKey="score" stroke="#8b5cf6" strokeWidth={3} dot={{ r: 4, fill: '#8b5cf6', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
           )}
        </div>
      </div>

      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft dark:shadow-soft-dark overflow-hidden">
        <div className="px-6 py-4 border-b border-border-light dark:border-border-dark flex items-center justify-between">
          <h2 className="text-lg font-semibold">Active Repositories</h2>
          <button
            onClick={() => fetchRepos(false)}
            className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 flex items-center space-x-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>
        <div className="divide-y divide-border-light dark:divide-border-dark">
          {loading ? (
            <div className="p-6 text-center text-slate-500">Loading repositories...</div>
          ) : repoError ? (
            <div role="alert" className="p-6 text-center text-red-600 dark:text-red-400">{repoError}</div>
          ) : repos.length === 0 ? (
            <div className="p-12 text-center space-y-4">
              <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400">
                <GitCommit className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-slate-900 dark:text-white">No repositories connected</h3>
                <p className="text-sm text-slate-500 max-w-sm mx-auto">
                  Connect a public or private GitHub repository to start continuous security monitoring, commit audits, and risk tracking.
                </p>
              </div>
              <button
                onClick={() => navigate('/onboarding')}
                className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors shadow-sm font-medium text-sm inline-flex items-center space-x-2"
              >
                <span>+ Add Repository</span>
              </button>
            </div>
          ) : (
            repos.map((repo: any) => (
              <div
                key={repo.id}
                className={`px-6 py-6 flex flex-col space-y-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group cursor-pointer ${
                  activeRepoId === repo.id.toString() ? 'border-l-4 border-brand-500 bg-slate-50/50 dark:bg-slate-800/30' : ''
                }`}
                onClick={() => handleRepoChange({ target: { value: repo.id.toString() } })}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                      <GitCommit className="w-5 h-5 text-slate-500" />
                    </div>
                    <div>
                      <h4 className="font-medium text-lg hover:text-brand-500 transition-colors">{repo.name}</h4>
                      <p className="text-sm text-slate-500">{repo.url}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 sm:space-x-3">
                    <button
                      onClick={() => navigate(`/hub/${repo.id}`)}
                      className="px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium rounded-lg bg-brand-500 hover:bg-brand-600 text-white flex items-center space-x-1.5 transition-colors shadow-sm"
                    >
                      <Compass className="w-4 h-4" />
                      <span>Project Hub</span>
                    </button>
                    <button
                      disabled={scanningRepoId === repo.id || isDeleting}
                      onClick={(e) => handleManualScan(repo, e)}
                      className={`px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 ${
                        scanningRepoId === repo.id
                          ? 'bg-slate-300 dark:bg-slate-700 text-slate-600 dark:text-slate-300 cursor-not-allowed'
                          : 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-slate-100'
                      }`}
                    >
                      {scanningRepoId === repo.id && <Loader2 className="w-4 h-4 animate-spin" />}
                      <span>{scanningRepoId === repo.id ? 'Scanning...' : 'Manual Scan Now'}</span>
                    </button>
                    <button
                      type="button"
                      disabled={isDeleting}
                      onClick={(e) => handleOpenDeleteDialog(repo, e)}
                      className="px-3 py-2 text-xs sm:text-sm font-medium rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 border border-transparent hover:border-red-200 dark:hover:border-red-900/50 transition-colors flex items-center space-x-1.5"
                      title="Remove repository from Zylorun"
                      aria-label={`Remove repository ${repo.name}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Remove</span>
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-4 border-t border-border-light dark:border-border-dark">
                  <div>
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Monitoring Status</p>
                    <div className="flex items-center space-x-2">
                      <div className="relative flex h-3 w-3">
                        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${repo.last_poll_error ? 'bg-red-400' : 'bg-emerald-400'}`}></span>
                        <span className={`relative inline-flex rounded-full h-3 w-3 ${repo.last_poll_error ? 'bg-red-500' : 'bg-emerald-500'}`}></span>
                      </div>
                      <p className={`font-medium ${repo.last_poll_error ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                        {repo.last_poll_error ? 'POLLING FAILED' : (repo.monitoring_status ? repo.monitoring_status.replace('_', ' ') : 'NOT CONFIGURED')}
                      </p>
                    </div>
                    {repo.last_poll_error && (
                      <p className="text-xs text-red-500 mt-1 truncate" title={repo.last_poll_error}>{repo.last_poll_error}</p>
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Last Polled</p>
                    <p className="font-medium text-sm">
                      {repo.last_polled_at ? new Date(repo.last_polled_at).toLocaleString() : 'Never'}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Success: {repo.last_successful_poll_at ? new Date(repo.last_successful_poll_at).toLocaleTimeString() : 'Never'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Sync Status</p>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-sm bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded text-slate-700 dark:text-slate-300">
                        {repo.last_processed_sha ? repo.last_processed_sha.substring(0, 7) : 'None'}
                      </span>
                      <span className="text-slate-400">&rarr;</span>
                      <span className="font-mono text-sm bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded text-slate-700 dark:text-slate-300">
                        {repo.last_seen_sha ? repo.last_seen_sha.substring(0, 7) : 'None'}
                      </span>
                    </div>
                    {repo.last_processed_sha && repo.last_seen_sha && repo.last_processed_sha === repo.last_seen_sha && (
                       <p className="text-xs text-emerald-500 mt-1 flex items-center"><CheckCircle2 className="w-3 h-3 mr-1" /> Fully Synced</p>
                    )}
                    {repo.last_processed_sha && repo.last_seen_sha && repo.last_processed_sha !== repo.last_seen_sha && (
                       <p className="text-xs text-amber-500 mt-1 flex items-center"><Activity className="w-3 h-3 mr-1" /> Processing backlog...</p>
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Current Security Score</p>
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">
                      {activeRepoId === repo.id.toString() && history.length > 0 ? (history[history.length - 1].score !== null ? `${history[history.length - 1].score}/100` : 'N/A') : '--'}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft dark:shadow-soft-dark overflow-hidden">
        <div className="px-6 py-4 border-b border-border-light dark:border-border-dark flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Commit Intelligence</h2>
        </div>
        <div className="divide-y divide-border-light dark:divide-border-dark">
          {historyLoading ? (
            <div className="p-6 space-y-4">
               <div className="h-6 w-1/3 bg-slate-200 dark:bg-slate-800 animate-pulse rounded"></div>
               <div className="h-6 w-1/2 bg-slate-200 dark:bg-slate-800 animate-pulse rounded"></div>
               <div className="h-6 w-1/4 bg-slate-200 dark:bg-slate-800 animate-pulse rounded"></div>
            </div>
          ) : history.length === 0 ? (
            <div className="p-6 text-center text-slate-500">No commits analyzed yet.</div>
          ) : (
            history.slice().reverse().slice(0, 5).map((h: any, idx) => (
              <div
                key={idx}
                className="px-6 py-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group cursor-pointer"
                onClick={() => navigate(`/repositories/${h.repoId}/scans/${h.scanId}/audit`)}
              >
                <div>
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="font-mono text-sm font-semibold text-slate-700 dark:text-slate-300">{h.commit}</span>
                    <span className="text-xs text-slate-500">{h.date}</span>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-sm">
                      {h.scoreDelta === null ? (
                        <>Baseline Score: <span className="font-semibold">{h.score}</span></>
                      ) : (
                        <>Security Score: <span className="font-semibold">{h.score !== null && h.scoreDelta !== null ? h.score - h.scoreDelta : '--'}</span> &rarr; <span className="font-semibold">{h.score}</span></>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      {h.findingsCount === 0 ? (
                        <span className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 px-2 py-0.5 rounded-full font-medium">
                          0 Actionable Issues
                        </span>
                      ) : (
                        <span className="text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 px-2 py-0.5 rounded-full font-medium">
                          {h.findingsCount} issue(s)
                        </span>
                      )}
                    </div>
                    {h.alerts && h.alerts.length > 0 && (
                      <div className="flex items-center space-x-2">
                        {h.alerts.map((alert: string, i: number) => (
                          <span key={i} className="text-xs bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 px-2 py-0.5 rounded-full font-medium">
                            {alert}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-brand-500 opacity-0 group-hover:opacity-100 transition-opacity flex items-center space-x-1 text-sm font-medium">
                  <span>View Details</span>
                  <span>&rarr;</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Confirmation Dialog for Safe Repository Removal */}
      {deleteDialogOpen && repoToDelete && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-dialog-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm"
          onClick={() => !isDeleting && setDeleteDialogOpen(false)}
        >
          <div
            className="w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl p-6 sm:p-8 space-y-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start space-x-4">
              <div className="w-12 h-12 rounded-xl bg-red-100 dark:bg-red-950/60 border border-red-200 dark:border-red-900 flex items-center justify-center text-red-600 dark:text-red-400 shrink-0">
                <AlertCircle className="w-6 h-6" />
              </div>
              <div className="space-y-1 flex-1 min-w-0">
                <h3 id="delete-dialog-title" className="text-xl font-bold text-slate-900 dark:text-white">
                  Remove Repository
                </h3>
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 truncate" title={repoToDelete.name}>
                  {repoToDelete.name}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 truncate" title={repoToDelete.url}>
                  {repoToDelete.url}
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
              <p>
                Remove this repository from Zylorun? Its stored scans, findings, risk history and repository-specific audit records will be deleted. The actual GitHub repository and its source code will not be deleted.
              </p>
            </div>

            {deleteError && (
              <div role="alert" className="p-3 rounded-lg bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{deleteError}</span>
              </div>
            )}

            <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 pt-2">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => {
                  setDeleteDialogOpen(false);
                  setRepoToDelete(null);
                  setDeleteError('');
                }}
                className="px-4 py-2.5 text-sm font-medium rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={handleConfirmDelete}
                className="px-4 py-2.5 text-sm font-medium rounded-xl bg-red-600 hover:bg-red-700 text-white shadow-sm transition-colors flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Removing Repository...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    <span>Remove Repository</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Autonomous Cyber Scanning Radar HUD */}
      <ScanningHUD
        isOpen={hudOpen}
        repoName={hudRepo?.name || 'Repository'}
        commitSha={hudCommitSha}
        scanStatus={hudStatus}
        scanId={hudScanId}
        riskScore={hudScore}
        actionableFindingsCount={hudActionableCount}
        fixturesCount={hudFixturesCount}
        errorMessage={hudError}
        onClose={() => setHudOpen(false)}
        onViewAudit={(sId) => {
          setHudOpen(false);
          navigate(`/repositories/${hudRepo?.id}/scans/${sId}/audit`);
        }}
        onDownloadPdf={(sId) => {
          window.open(`${apiClient.defaults.baseURL}/repositories/${hudRepo?.id}/scans/${sId}/report.pdf`, '_blank');
        }}
        onRetry={() => {
          if (hudRepo) handleManualScan(hudRepo, { stopPropagation: () => {} } as any);
        }}
      />
    </div>
  );
}
