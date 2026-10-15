import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../config';
import { Shield, GitCommit, CheckCircle, ShieldAlert, Activity, ExternalLink, Layers } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export default function RiskPassport() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [repo, setRepo] = useState<any>(null);
  const [repos, setRepos] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [latestScan, setLatestScan] = useState<any>(null);
  const [needsSelection, setNeedsSelection] = useState(false);
  const [activeRepoId, setActiveRepoId] = useState<string | null>(localStorage.getItem('gitflow_active_repo') || null);

  const fetchRepoData = useCallback(async (targetRepo: any, silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      setRepo(targetRepo);
      // 1. Get history
      const histRes = await apiClient.get(`/repositories/${targetRepo.id}/risk-history`);
      setHistory(histRes.data);

      // 2. Get latest scan if exists
      if (histRes.data.length > 0) {
        const latest = histRes.data[histRes.data.length - 1];
        const scanRes = await apiClient.get(`/repositories/${targetRepo.id}/scans/${latest.id}`);
        setLatestScan(scanRes.data);
      } else {
        setLatestScan(null);
      }
    } catch (err: any) {
      console.error('Failed to load repo scan details', err);
      if (!silent) setError('Failed to load Security Passport data.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  const handleRepoChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedId = e.target.value;
    setActiveRepoId(selectedId);
    localStorage.setItem('gitflow_active_repo', selectedId);
    const target = repos.find((r: any) => r.id.toString() === selectedId);
    if (target) {
      fetchRepoData(target, false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    let hasLoaded = false;

    const initData = async () => {
      if (inFlight) return;
      inFlight = true;
      if (!hasLoaded) setLoading(true);

      try {
        const repoRes = await apiClient.get('/repositories/');
        if (cancelled) return;
        const repoList = repoRes.data;
        setRepos(repoList);

        if (repoList.length === 0) {
          setRepo(null);
          setHistory([]);
          setLatestScan(null);
          setLoading(false);
          return;
        }

        let targetId = activeRepoId || localStorage.getItem('gitflow_active_repo');
        let activeRepo = repoList.find((r: any) => r.id.toString() === targetId);

        if (!activeRepo) {
          if (repoList.length === 1) {
            activeRepo = repoList[0];
            setActiveRepoId(activeRepo.id.toString());
            localStorage.setItem('gitflow_active_repo', activeRepo.id.toString());
          } else {
            setNeedsSelection(true);
            setLoading(false);
            return;
          }
        }

        setNeedsSelection(false);
        setActiveRepoId(activeRepo.id.toString());
        await fetchRepoData(activeRepo, hasLoaded);
      } catch (err: any) {
        console.error(err);
        if (!hasLoaded && !cancelled) setError('Failed to load Security Passport repositories.');
      } finally {
        inFlight = false;
        if (!cancelled) {
          hasLoaded = true;
          setLoading(false);
        }
      }
    };

    initData();

    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible' && repo) {
        fetchRepoData(repo, true);
      }
    }, 30000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [fetchRepoData]);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading Security Passport...</div>;
  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;

  if (needsSelection) {
    return (
      <div className="max-w-6xl mx-auto py-12 text-center">
        <Shield className="w-16 h-16 mx-auto text-slate-300 dark:text-slate-700 mb-4" />
        <h2 className="text-2xl font-bold mb-4 text-slate-800 dark:text-white">Select a Repository</h2>
        <select 
          className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-md px-4 py-2 text-base outline-none"
          onChange={handleRepoChange} 
          value=""
        >
          <option value="" disabled>Select a repository...</option>
          {repos.map((r: any) => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
      </div>
    );
  }

  if (!repo || history.length === 0 || !latestScan) {
    return (
      <div className="max-w-6xl mx-auto text-center py-12">
        <Shield className="w-16 h-16 mx-auto text-slate-300 dark:text-slate-700 mb-4" />
        <h1 className="text-2xl font-bold mb-2">Software Security Passport</h1>
        <p className="text-slate-500 dark:text-slate-400">Connect a repository and complete a scan to generate its Security Passport.</p>
        <div className="mt-6">
          <button
            onClick={() => navigate('/onboarding')}
            className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors shadow-sm font-medium text-sm"
          >
            Go to Onboarding &rarr;
          </button>
        </div>
      </div>
    );
  }

  const { risk_score, score_delta, findings = [], impact = {}, actions_detected = [], commit_sha, message, author, timestamp, status, category_scores = {} } = latestScan;
  
  const countSeverity = (sev: string) => findings.filter((f: any) => f.severity === sev).length;
  const countCategory = (cat: string) => findings.filter((f: any) => f.title === cat || f.category === cat).length;
  
  const chartData = history.map((h: any) => ({
    name: h.short_sha,
    score: h.risk_score
  }));

  const secScore = category_scores?.security ?? (countCategory('Vulnerability') > 0 ? Math.max(0, 100 - countCategory('Vulnerability') * 15) : 100);
  const secretScore = category_scores?.secrets ?? (countCategory('Secret') > 0 ? Math.max(0, 100 - countCategory('Secret') * 20) : 100);
  const depScore = category_scores?.dependencies ?? (countCategory('DependencyScan') > 0 ? Math.max(0, 100 - countCategory('DependencyScan') * 10) : 100);
  const licScore = category_scores?.licenses ?? (countCategory('License') > 0 ? 80 : 100);
  const qualScore = category_scores?.quality ?? (countCategory('Quality') > 0 ? 85 : 100);

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex justify-end mb-2">
        {repos.length > 1 && (
          <select 
            className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-md px-3 py-1.5 text-sm outline-none"
            value={repo.id.toString()}
            onChange={handleRepoChange}
          >
            {repos.map((r: any) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        )}
      </div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 dark:text-white flex items-center">
            <Shield className="w-8 h-8 mr-3 text-brand-500" />
            Software Security Passport
          </h1>
          <p className="text-slate-500 mt-1 flex items-center">
            <GitCommit className="w-4 h-4 mr-1" />
            {repo.name} &mdash; {repo.url}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate(`/repositories/${repo.id}/scans/${latestScan.id}/audit`)}
            className="px-3.5 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-lg shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <span>View Commit Audit</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
          <div className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
            <CheckCircle className="w-4 h-4 mr-1.5" />
            {status}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">Current Security Score</h3>
          <div className="flex items-end space-x-4">
            <span className={`text-6xl font-bold ${risk_score === 0 ? 'text-red-600 dark:text-red-500' : 'text-slate-800 dark:text-white'}`}>
              {status === 'FAILED' ? 'FAILED' : risk_score !== null ? risk_score : 'UNAVAILABLE'}
            </span>
            <div className="pb-2">
              <span className="text-sm text-slate-500 block">out of 100 {risk_score === 0 ? '(Critical)' : ''}</span>
              {score_delta !== null && (
                <span className={`text-sm font-medium ${score_delta < 0 ? 'text-emerald-500' : score_delta > 0 ? 'text-red-500' : 'text-slate-500'}`}>
                  {score_delta > 0 ? '+' : ''}{score_delta} from previous
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">Findings Summary</h3>
          <div className="flex items-center space-x-6">
            <div>
              <div className="text-3xl font-bold text-slate-800 dark:text-white">{findings.length}</div>
              <div className="text-xs text-slate-500">Total</div>
            </div>
            <div className="flex-1 grid grid-cols-2 gap-2 text-sm">
              <div className="flex justify-between items-center bg-red-50 dark:bg-red-900/10 px-2 py-1 rounded text-red-700 dark:text-red-400">
                <span>Critical</span> <span className="font-bold">{countSeverity('Critical')}</span>
              </div>
              <div className="flex justify-between items-center bg-orange-50 dark:bg-orange-900/10 px-2 py-1 rounded text-orange-700 dark:text-orange-400">
                <span>High</span> <span className="font-bold">{countSeverity('High')}</span>
              </div>
              <div className="flex justify-between items-center bg-amber-50 dark:bg-amber-900/10 px-2 py-1 rounded text-amber-700 dark:text-amber-400">
                <span>Medium</span> <span className="font-bold">{countSeverity('Medium')}</span>
              </div>
              <div className="flex justify-between items-center bg-blue-50 dark:bg-blue-900/10 px-2 py-1 rounded text-blue-700 dark:text-blue-400">
                <span>Low</span> <span className="font-bold">{countSeverity('Low')}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">Latest Commit</h3>
          <div className="space-y-2">
            <div className="font-mono text-sm text-slate-800 dark:text-slate-200 truncate">{commit_sha}</div>
            <div className="text-sm text-slate-600 dark:text-slate-400 truncate">{message || 'No message'}</div>
            <div className="text-xs text-slate-500 flex items-center justify-between mt-4">
              <span>{author || 'Unknown'}</span>
              <span>{timestamp ? new Date(timestamp).toLocaleString() : 'Prior to tracking'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Category Scores Sub-Breakdown */}
      <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
        <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4 flex items-center">
          <Layers className="w-4 h-4 mr-2" /> Defensible Category Scores
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
          <div className="p-3 rounded-lg border border-border-light dark:border-border-dark bg-slate-50/50 dark:bg-slate-800/40">
            <p className="text-xs text-slate-500 mb-1">Code SAST</p>
            <p className="text-xl font-bold text-slate-900 dark:text-white">{secScore}<span className="text-xs font-normal text-slate-500">/100</span></p>
          </div>
          <div className="p-3 rounded-lg border border-border-light dark:border-border-dark bg-slate-50/50 dark:bg-slate-800/40">
            <p className="text-xs text-slate-500 mb-1">Secret Detection</p>
            <p className="text-xl font-bold text-slate-900 dark:text-white">{secretScore}<span className="text-xs font-normal text-slate-500">/100</span></p>
          </div>
          <div className="p-3 rounded-lg border border-border-light dark:border-border-dark bg-slate-50/50 dark:bg-slate-800/40">
            <p className="text-xs text-slate-500 mb-1">Dependencies</p>
            <p className="text-xl font-bold text-slate-900 dark:text-white">{depScore}<span className="text-xs font-normal text-slate-500">/100</span></p>
          </div>
          <div className="p-3 rounded-lg border border-border-light dark:border-border-dark bg-slate-50/50 dark:bg-slate-800/40">
            <p className="text-xs text-slate-500 mb-1">Open Source License</p>
            <p className="text-xl font-bold text-slate-900 dark:text-white">{licScore}<span className="text-xs font-normal text-slate-500">/100</span></p>
          </div>
          <div className="p-3 rounded-lg border border-border-light dark:border-border-dark bg-slate-50/50 dark:bg-slate-800/40">
            <p className="text-xs text-slate-500 mb-1">Quality & Hygiene</p>
            <p className="text-xl font-bold text-slate-900 dark:text-white">{qualScore}<span className="text-xs font-normal text-slate-500">/100</span></p>
          </div>
        </div>
      </div>

      <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
        <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-6">Security History</h3>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.2} />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
              <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                itemStyle={{ color: '#10b981' }}
              />
              <Area type="monotone" dataKey="score" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorScore)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4 flex items-center">
            <Activity className="w-4 h-4 mr-2" /> Change Intelligence
          </h3>
          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Actions Detected</h4>
              {actions_detected && actions_detected.length > 0 ? (
                <ul className="space-y-2">
                  {actions_detected.map((action: string, i: number) => (
                    <li key={i} className="text-sm flex items-center text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800 p-2 rounded">
                      <div className="w-1.5 h-1.5 rounded-full bg-brand-500 mr-2" />
                      {action}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">No high-level actions identified.</p>
              )}
            </div>
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Impact Analysis</h4>
              {impact && Object.keys(impact).length > 0 ? (
                <div className="text-sm space-y-2 bg-slate-50 dark:bg-slate-800 p-3 rounded">
                  <div><span className="font-semibold">Directly Changed:</span> {Array.isArray(impact.directly_changed) ? impact.directly_changed.join(', ') : impact.directly_changed || 'None'}</div>
                  <div><span className="font-semibold">Potentially Affected:</span> {Array.isArray(impact.potentially_affected) ? impact.potentially_affected.join(', ') : impact.potentially_affected || 'None'}</div>
                  <div className="text-slate-500 italic mt-1">{impact.reason || 'No specific impact reason.'}</div>
                </div>
              ) : (
                <p className="text-sm text-slate-500">Impact analysis not available.</p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4 flex items-center">
            <ShieldAlert className="w-4 h-4 mr-2" /> Category Breakdown
          </h3>
          <div className="space-y-4">
             <div className="flex items-center justify-between text-sm border-b border-slate-100 dark:border-slate-800 pb-2">
               <span className="text-slate-600 dark:text-slate-400">Security / SAST</span>
               <span className="font-semibold">{countCategory('Vulnerability')}</span>
             </div>
             <div className="flex items-center justify-between text-sm border-b border-slate-100 dark:border-slate-800 pb-2">
               <span className="text-slate-600 dark:text-slate-400">Secrets Detected</span>
               <span className="font-semibold">{countCategory('Secret')}</span>
             </div>
             <div className="flex items-center justify-between text-sm border-b border-slate-100 dark:border-slate-800 pb-2">
               <span className="text-slate-600 dark:text-slate-400">Vulnerable Dependencies</span>
               <span className="font-semibold">{countCategory('DependencyScan')}</span>
             </div>
             <div className="flex items-center justify-between text-sm border-b border-slate-100 dark:border-slate-800 pb-2">
               <span className="text-slate-600 dark:text-slate-400">License Issues</span>
               <span className="font-semibold">{countCategory('License')}</span>
             </div>
             <div className="flex items-center justify-between text-sm">
               <span className="text-slate-600 dark:text-slate-400">Quality & Hygiene</span>
               <span className="font-semibold">{countCategory('Quality') + countCategory('Architecture')}</span>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
