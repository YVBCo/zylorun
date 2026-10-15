import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  Code2,
  Cpu,
  Database,
  FileCode,
  GitBranch,
  GitCommit,
  Layers,
  RefreshCw,
  Sparkles,
  Plus,
  Trash2,
  Play,
  Check,
  Send,
  MessageSquare,
  Rocket,
  Radio,
  BookOpen,
  Users,
  Compass,
  Zap,
  ShieldAlert,
  CheckSquare,
  Wrench,
  HelpCircle,
  ShieldCheck,
  Info,
} from 'lucide-react';
import { apiClient } from '../config';
import FeatureExplainerModal from '../components/FeatureExplainerModal';

interface RepoSummary {
  id: number;
  name: string;
  github_url: string;
  default_branch: string;
  last_processed_sha?: string;
  last_successful_poll_at?: string;
  ai_enabled?: boolean;
}

export default function ProjectHub() {
  const { repositoryId } = useParams();
  const navigate = useNavigate();

  // State
  const [repos, setRepos] = useState<RepoSummary[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(
    repositoryId ? parseInt(repositoryId, 10) : null
  );
  const [activeTab, setActiveTab] = useState<
    | 'overview'
    | 'analyzers'
    | 'timemachine'
    | 'watchtower'
    | 'issues'
    | 'memory'
    | 'releases'
    | 'aiexpert'
    | 'radar'
  >('overview');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Tab Data States
  const [overviewData, setOverviewData] = useState<any>(null);
  const [analyzersData, setAnalyzersData] = useState<any[]>([]);
  const [timeMachineData, setTimeMachineData] = useState<any>(null);
  const [watchtowerEvents, setWatchtowerEvents] = useState<any[]>([]);
  const [issuesData, setIssuesData] = useState<any[]>([]);
  const [ownershipData, setOwnershipData] = useState<any>(null);
  const [memories, setMemories] = useState<any[]>([]);
  const [releasesData, setReleasesData] = useState<any[]>([]);
  const [crossRepoData, setCrossRepoData] = useState<any>(null);

  // Forms / Interactivity States
  const [runningAnalyzers, setRunningAnalyzers] = useState(false);
  const [newMemoryCategory, setNewMemoryCategory] = useState('DECISION');
  const [newMemoryTitle, setNewMemoryTitle] = useState('');
  const [newMemoryContent, setNewMemoryContent] = useState('');
  const [newMemoryTags, setNewMemoryTags] = useState('');

  const [newIssueTitle, setNewIssueTitle] = useState('');
  const [newIssueDesc, setNewIssueDesc] = useState('');
  const [newIssueSeverity, setNewIssueSeverity] = useState('Medium');

  const [releaseTag, setReleaseTag] = useState('');
  const [releaseNotes, setReleaseNotes] = useState('');

  const [aiQuestion, setAiQuestion] = useState('');
  const [aiResponse, setAiResponse] = useState<any>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const [completenessCriteria, setCompletenessCriteria] = useState('');
  const [completenessResult, setCompletenessResult] = useState<any>(null);
  const [completenessLoading, setCompletenessLoading] = useState(false);

  const [fixCandidateFindingId, setFixCandidateFindingId] = useState('');
  const [fixCandidateResult, setFixCandidateResult] = useState<any>(null);
  const [fixCandidateLoading, setFixCandidateLoading] = useState(false);

  // Advanced Analyzer & AI State
  const [runningSingle, setRunningSingle] = useState<string | null>(null);
  const [aiStatus, setAiStatus] = useState<any>(null);
  const [aiTestingConnection, setAiTestingConnection] = useState(false);
  const [aiConnectionResult, setAiConnectionResult] = useState<any>(null);
  const [showExplainer, setShowExplainer] = useState(false);
  const [explainerInitial, setExplainerInitial] = useState<string>('overview');

  // 1. Initial Load: Fetch Repositories
  useEffect(() => {
    async function loadRepos() {
      try {
        setLoading(true);
        const res = await apiClient.get('/repositories/');
        setRepos(res.data);
        if (res.data.length > 0) {
          if (!selectedRepoId || !res.data.some((r: any) => r.id === selectedRepoId)) {
            setSelectedRepoId(res.data[0].id);
          }
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load repositories');
      } finally {
        setLoading(false);
      }
    }
    loadRepos();
  }, [repositoryId]);

  // 2. Fetch Active Tab Data when selectedRepoId or activeTab changes
  const fetchTabData = useCallback(async () => {
    if (!selectedRepoId) return;
    setError('');

    try {
      if (activeTab === 'overview') {
        const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/overview`);
        setOverviewData(res.data);
      } else if (activeTab === 'analyzers') {
        const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/analyzers`);
        setAnalyzersData(res.data.analyzers || res.data || []);
      } else if (activeTab === 'timemachine') {
        const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/time-machine`);
        setTimeMachineData(res.data);
      } else if (activeTab === 'watchtower') {
        const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/watchtower`);
        setWatchtowerEvents(res.data.events || []);
      } else if (activeTab === 'issues') {
        const [issuesRes, ownerRes] = await Promise.all([
          apiClient.get(`/repositories/${selectedRepoId}/hub/issues`),
          apiClient.get(`/repositories/${selectedRepoId}/hub/ownership`),
        ]);
        setIssuesData(issuesRes.data || []);
        setOwnershipData(ownerRes.data || null);
      } else if (activeTab === 'memory') {
        const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/memory`);
        setMemories(res.data || []);
      } else if (activeTab === 'releases') {
        const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/releases`);
        setReleasesData(res.data || []);
      } else if (activeTab === 'aiexpert') {
        try {
          const statusRes = await apiClient.get(`/repositories/${selectedRepoId}/hub/ai/status`);
          setAiStatus(statusRes.data);
        } catch (e) {
          console.error('Failed to load AI status:', e);
        }
      } else if (activeTab === 'radar') {
        const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/cross-repo`);
        setCrossRepoData(res.data || null);
      }
    } catch (err: any) {
      console.error('Error fetching hub data:', err);
    }
  }, [selectedRepoId, activeTab]);

  useEffect(() => {
    fetchTabData();
  }, [fetchTabData]);

  // Periodic polling for Watchtower feed if open
  useEffect(() => {
    if (activeTab !== 'watchtower' || !selectedRepoId) return;
    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/watchtower`);
        setWatchtowerEvents(res.data.events || []);
      } catch (e) {
        // quiet
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [activeTab, selectedRepoId]);

  // Handlers
  const handleRunAnalyzers = async () => {
    if (!selectedRepoId) return;
    setRunningAnalyzers(true);
    setSuccessMsg('');
    setError('');
    try {
      const res = await apiClient.post(`/repositories/${selectedRepoId}/hub/analyzers/run`);
      setAnalyzersData(res.data.analyzers || []);
      setSuccessMsg(res.data.summary || 'All 10 continuous analyzers executed and results persisted successfully!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to execute analyzers');
    } finally {
      setRunningAnalyzers(false);
    }
  };

  const handleRunSingleAnalyzer = async (analyzerName: string) => {
    if (!selectedRepoId) return;
    setRunningSingle(analyzerName);
    setError('');
    try {
      const res = await apiClient.post(`/repositories/${selectedRepoId}/hub/analyzers/run`, {
        analyzers: [analyzerName],
      });
      const updatedRuns = res.data.analyzers || [];
      if (updatedRuns.length > 0) {
        setAnalyzersData((prev) =>
          prev.map((a) => {
            const found = updatedRuns.find(
              (u: any) => u.name === a.name || u.analyzer_name === a.name
            );
            return found ? { ...a, ...found } : a;
          })
        );
      }
      setSuccessMsg(`Analyzer '${analyzerName.replace(/_/g, ' ')}' executed and saved!`);
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to run analyzer '${analyzerName}'`);
    } finally {
      setRunningSingle(null);
    }
  };

  const handleTestAiConnection = async () => {
    if (!selectedRepoId) return;
    setAiTestingConnection(true);
    setAiConnectionResult(null);
    try {
      const res = await apiClient.post(`/repositories/${selectedRepoId}/hub/ai/test-connection`);
      setAiConnectionResult(res.data);
      const statusRes = await apiClient.get(`/repositories/${selectedRepoId}/hub/ai/status`);
      setAiStatus(statusRes.data);
    } catch (err: any) {
      setAiConnectionResult({
        success: false,
        latency_ms: 0,
        provider: 'none',
        model: 'none',
        message: err.response?.data?.detail || 'AI connection test failed',
      });
    } finally {
      setAiTestingConnection(false);
    }
  };

  const renderProvenanceBadge = (item: any) => {
    if (!item) return null;
    const mode = item.execution_mode || (item.ai_available ? 'real_provider' : 'deterministic_fallback');
    const isCached = item.cached;
    const providerName = item.provider || 'system';
    const modelName = item.model || '';

    return (
      <div className="flex flex-wrap items-center gap-1.5 mt-2">
        {mode === 'real_provider' && (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Sparkles className="w-3 h-3" />
            AI-Generated ({modelName || providerName})
          </span>
        )}
        {mode === 'mock_provider' && (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Cpu className="w-3 h-3" />
            Mock Mode (Local Development)
          </span>
        )}
        {mode === 'deterministic_fallback' && (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Zap className="w-3 h-3" />
            Deterministic Fallback (Rule-Based Engine)
          </span>
        )}
        {isCached && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
            <Clock className="w-2.5 h-2.5" />
            Cached Result
          </span>
        )}
      </div>
    );
  };

  const handleSaveMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepoId || !newMemoryTitle.trim() || !newMemoryContent.trim()) return;
    try {
      const tagsList = newMemoryTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      await apiClient.post(`/repositories/${selectedRepoId}/hub/memory`, {
        category: newMemoryCategory,
        title: newMemoryTitle,
        content: newMemoryContent,
        tags: tagsList,
      });
      setNewMemoryTitle('');
      setNewMemoryContent('');
      setNewMemoryTags('');
      setSuccessMsg('Project memory saved successfully.');
      const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/memory`);
      setMemories(res.data || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save project memory');
    }
  };

  const handleDeleteMemory = async (memoryId: number) => {
    if (!selectedRepoId) return;
    try {
      await apiClient.delete(`/repositories/${selectedRepoId}/hub/memory/${memoryId}`);
      setMemories((prev) => prev.filter((m) => m.id !== memoryId));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete memory');
    }
  };

  const handleCreateIssue = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepoId || !newIssueTitle.trim()) return;
    try {
      await apiClient.post(`/repositories/${selectedRepoId}/hub/issues`, {
        title: newIssueTitle,
        description: newIssueDesc,
        severity: newIssueSeverity,
      });
      setNewIssueTitle('');
      setNewIssueDesc('');
      setSuccessMsg('Issue task created successfully.');
      const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/issues`);
      setIssuesData(res.data || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create issue');
    }
  };

  const handlePrepareRelease = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepoId || !releaseTag.trim()) return;
    try {
      await apiClient.post(`/repositories/${selectedRepoId}/hub/releases`, {
        version_tag: releaseTag,
        target_commit_sha: 'HEAD',
        release_notes: releaseNotes,
      });
      setReleaseTag('');
      setReleaseNotes('');
      setSuccessMsg('Release candidate prepared successfully.');
      const res = await apiClient.get(`/repositories/${selectedRepoId}/hub/releases`);
      setReleasesData(res.data || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to prepare release');
    }
  };

  const handleAskAi = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepoId || !aiQuestion.trim()) return;
    setAiLoading(true);
    setAiResponse(null);
    try {
      const res = await apiClient.post(`/repositories/${selectedRepoId}/hub/ai/ask`, {
        question: aiQuestion,
      });
      setAiResponse(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'AI Assistant request failed');
    } finally {
      setAiLoading(false);
    }
  };

  const handleCheckCompleteness = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepoId || !completenessCriteria.trim()) return;
    setCompletenessLoading(true);
    setCompletenessResult(null);
    try {
      const res = await apiClient.post(
        `/repositories/${selectedRepoId}/hub/ai/feature-completeness`,
        { spec_or_criteria: completenessCriteria }
      );
      setCompletenessResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Completeness check failed');
    } finally {
      setCompletenessLoading(false);
    }
  };

  const handleGenerateFixCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepoId || !fixCandidateFindingId.trim()) return;
    const fid = parseInt(fixCandidateFindingId, 10);
    if (isNaN(fid)) return;
    setFixCandidateLoading(true);
    setFixCandidateResult(null);
    try {
      const res = await apiClient.post(
        `/repositories/${selectedRepoId}/hub/findings/${fid}/fix`
      );
      setFixCandidateResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Candidate fix generation failed');
    } finally {
      setFixCandidateLoading(false);
    }
  };

  const currentRepo = repos.find((r) => r.id === selectedRepoId);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-8">
        <div className="flex items-center gap-3 text-slate-400">
          <RefreshCw className="w-5 h-5 animate-spin text-brand-400" />
          <span>Loading GitFlow Project Hub...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8 space-y-8">
      {/* 1. Header & Repository Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
                GitFlow Project Hub
                <span className="text-xs uppercase px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 font-semibold">
                  Unified Intelligence
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Continuous codebase intelligence, 10 specialized analyzers, living project memory & release readiness
              </p>
              {currentRepo && (
                <div className="text-xs text-slate-400 mt-1">
                  Active Repository: <b className="text-white">{currentRepo.name}</b> (branch: {currentRepo.default_branch || 'main'})
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Repository Selector Dropdown & Quick Actions */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <select
              value={selectedRepoId || ''}
              onChange={(e) => {
                const id = parseInt(e.target.value, 10);
                setSelectedRepoId(id);
                navigate(`/hub/${id}`);
              }}
              className="bg-slate-900 border border-slate-700 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-brand-500 font-medium"
            >
              {repos.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.default_branch || 'main'})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => {
              setExplainerInitial(activeTab);
              setShowExplainer(true);
            }}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-brand-500/10 hover:bg-brand-500/20 text-brand-400 border border-brand-500/30 text-xs font-semibold transition shadow-sm"
            title="Explore Feature & Architecture Guide"
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Feature Guide</span>
          </button>

          <button
            onClick={fetchTabData}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition"
            title="Refresh current tab"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Notifications / Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError('')} className="text-xs hover:underline">
            Dismiss
          </button>
        </div>
      )}
      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg('')} className="text-xs hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* 2. Hub Navigation Tabs */}
      <div className="border-b border-slate-800">
        <nav className="flex space-x-2 md:space-x-4 overflow-x-auto pb-2 scrollbar-none">
          {[
            { id: 'overview', label: 'Overview & DNA', icon: Cpu },
            { id: 'analyzers', label: 'Analyzer Suite (10)', icon: Layers },
            { id: 'timemachine', label: 'Time Machine & Impact', icon: Clock },
            { id: 'watchtower', label: 'Watchtower Live', icon: Radio },
            { id: 'issues', label: 'Issues & Tasks', icon: CheckSquare },
            { id: 'memory', label: 'Project Memory', icon: BookOpen },
            { id: 'releases', label: 'Release Readiness', icon: Rocket },
            { id: 'aiexpert', label: 'AI Expert & Fix Agent', icon: Sparkles },
            { id: 'radar', label: 'Cross-Repo Radar', icon: GitBranch },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition whitespace-nowrap ${
                  isActive
                    ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/20'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* 3. Tab Contents */}

      {/* TAB 1: OVERVIEW & DNA */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {overviewData ? (
            <>
              {/* Architecture DNA Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Health Score</span>
                    <Activity className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-white">
                    {overviewData.health_metrics?.score || 100}
                    <span className="text-sm font-normal text-slate-400">/100</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-2">
                    {overviewData.health_metrics?.status || 'Good Status'}
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Open Findings</span>
                    <ShieldAlert className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-white">
                    {overviewData.open_findings_count || 0}
                  </div>
                  <div className="text-xs text-slate-400 mt-2">
                    Across Security, Secrets & Quality
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Total Commits</span>
                    <GitCommit className="w-4 h-4 text-blue-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-white">
                    {overviewData.total_commits || 0}
                  </div>
                  <div className="text-xs text-slate-400 mt-2">
                    Tracked in GitFlow timeline
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Discovered Routes</span>
                    <FileCode className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-white">
                    {overviewData.architecture?.routes_count || 0}
                  </div>
                  <div className="text-xs text-slate-400 mt-2">
                    API Endpoints discovered
                  </div>
                </div>
              </div>

              {/* Frameworks & Languages Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
                  <h3 className="text-base font-semibold text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-brand-400" />
                    Detected Frameworks & Runtimes
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {overviewData.architecture?.frameworks?.map((fw: string) => (
                      <span
                        key={fw}
                        className="px-3 py-1 rounded-lg text-xs font-medium bg-brand-500/10 text-brand-400 border border-brand-500/20"
                      >
                        {fw}
                      </span>
                    )) || <span className="text-sm text-slate-500">None detected</span>}
                  </div>

                  <h3 className="text-base font-semibold text-white flex items-center gap-2 pt-2">
                    <Code2 className="w-4 h-4 text-emerald-400" />
                    Primary Languages
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {overviewData.architecture?.languages?.map((lang: string) => (
                      <span
                        key={lang}
                        className="px-3 py-1 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      >
                        {lang}
                      </span>
                    )) || <span className="text-sm text-slate-500">None detected</span>}
                  </div>
                </div>

                <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
                  <h3 className="text-base font-semibold text-white flex items-center gap-2">
                    <Database className="w-4 h-4 text-amber-400" />
                    Data Models & Schemas
                  </h3>
                  <div className="text-sm text-slate-300">
                    Discovered {overviewData.architecture?.models_count || 0} database entity models and schemas.
                  </div>
                  <div className="text-xs text-slate-400">
                    ORM mapping and migration consistency verified through Database & Migration Analyzer.
                  </div>

                  <h3 className="text-base font-semibold text-white flex items-center gap-2 pt-2">
                    <Zap className="w-4 h-4 text-blue-400" />
                    Test Suite Coverage
                  </h3>
                  <div className="text-sm text-slate-300">
                    Discovered {overviewData.architecture?.tests_count || 0} automated test files.
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-slate-500">Loading overview data...</div>
          )}
        </div>
      )}

      {/* TAB 2: ANALYZER CENTER (10 SUITES) */}
      {activeTab === 'analyzers' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Continuous Analyzer Suite</h2>
              <p className="text-xs text-slate-400">
                10 specialized static and contract analyzers running incrementally across the codebase.
              </p>
            </div>
            <button
              onClick={handleRunAnalyzers}
              disabled={runningAnalyzers}
              className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition shadow-sm"
            >
              {runningAnalyzers ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Running Suite...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run All 10 Analyzers
                </>
              )}
            </button>
          </div>

          {runningAnalyzers && (
            <div className="relative p-6 rounded-2xl bg-slate-950/90 border border-brand-500/40 cyber-glow-cyan overflow-hidden cyber-grid-bg animate-in fade-in duration-300">
              <div className="flex items-center gap-4">
                <div className="relative w-14 h-14 rounded-full bg-brand-500/10 border border-brand-500/30 flex items-center justify-center flex-shrink-0">
                  <div className="absolute inset-0 rounded-full animate-radar-sweep pointer-events-none" style={{ background: 'conic-gradient(from 0deg, transparent 0deg, rgba(14, 165, 233, 0.4) 360deg)' }} />
                  <Activity className="w-6 h-6 text-brand-400 animate-pulse" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-brand-400">Executing Continuous Intelligence Matrix</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 animate-pulse border border-brand-500/30">10 ANALYZERS RUNNING</span>
                  </div>
                  <div className="text-sm font-semibold text-white mt-1">
                    Analyzing AST topology, API contracts, database migrations, CI/CD pipelines & accessibility...
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {analyzersData.map((a: any, idx: number) => {
              const analyzerKey = a.name || a.analyzer_name || `analyzer_${idx}`;
              const isRunningThis = runningSingle === analyzerKey;
              const statusColor =
                a.status === 'COMPLETED'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : a.status === 'FAILED'
                  ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                  : a.status === 'PARTIAL'
                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  : 'bg-slate-800 text-slate-400 border border-slate-700';

              return (
                <div
                  key={analyzerKey}
                  className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center text-xs font-bold">
                        {idx + 1}
                      </span>
                      <h3 className="font-semibold text-white capitalize flex items-center gap-1.5">
                        {(a.label || a.name || a.analyzer_name || '').replace(/_/g, ' ')}
                        <button
                          onClick={() => {
                            setExplainerInitial(a.name || a.analyzer_name);
                            setShowExplainer(true);
                          }}
                          className="text-slate-500 hover:text-brand-400 transition"
                          title="Feature documentation & rationale"
                        >
                          <HelpCircle className="w-3.5 h-3.5" />
                        </button>
                      </h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-semibold ${statusColor}`}>
                        {a.status || 'NOT RUN'}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 font-medium">
                        {a.coverage_status || 'FULL'}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">{a.summary || a.description}</p>

                  <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/80">
                    <div>
                      Findings:{' '}
                      <span className={`font-semibold ${a.findings_count > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
                        {a.findings_count || 0}
                      </span>
                    </div>
                    <div>
                      Files: <span className="text-white font-semibold">{a.files_analyzed || 0}</span>
                    </div>
                    <div>Duration: {(a.duration_seconds || 0).toFixed(2)}s</div>
                    <button
                      onClick={() => handleRunSingleAnalyzer(analyzerKey)}
                      disabled={isRunningThis || runningAnalyzers}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-[11px] font-medium border border-slate-700 transition"
                    >
                      {isRunningThis ? (
                        <>
                          <RefreshCw className="w-3 h-3 animate-spin text-brand-400" />
                          <span>Running...</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3 h-3 text-brand-400" />
                          <span>Run</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Limitations & coverage disclaimer */}
                  {a.limitations && a.limitations.length > 0 && (
                    <div className="text-[11px] text-slate-400 italic bg-slate-950/60 p-2 rounded-lg border border-slate-800/60 flex items-start gap-1.5">
                      <span className="text-amber-400 font-bold not-italic">Scope:</span>
                      <span>{a.limitations[0]}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: TIME MACHINE & BLAST RADIUS */}
      {activeTab === 'timemachine' && (
        <div className="space-y-6">
          <h2 className="text-lg font-bold text-white">Time Machine & Change Impact</h2>
          {timeMachineData ? (
            <div className="space-y-4">
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800">
                <h3 className="font-semibold text-white mb-2">Change Impact & Blast Radius</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="text-xs uppercase font-semibold text-slate-400">Directly Changed</span>
                    <div className="text-2xl font-bold text-blue-400 mt-1">
                      {timeMachineData.impact?.directly_changed_count || 0}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="text-xs uppercase font-semibold text-slate-400">Shared Dependencies</span>
                    <div className="text-2xl font-bold text-amber-400 mt-1">
                      {timeMachineData.impact?.shared_dependencies_count || 0}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="text-xs uppercase font-semibold text-slate-400">Potentially Affected</span>
                    <div className="text-2xl font-bold text-purple-400 mt-1">
                      {timeMachineData.impact?.potentially_affected_count || 0}
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
                <h3 className="font-semibold text-white">Recent Commit Revisions</h3>
                <div className="space-y-2">
                  {timeMachineData.commits?.map((c: any) => (
                    <div
                      key={c.sha}
                      className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-3">
                        <GitCommit className="w-4 h-4 text-brand-400" />
                        <span className="font-mono text-slate-300">{c.sha?.substring(0, 7)}</span>
                        <span className="text-slate-200">{c.message}</span>
                      </div>
                      <span className="text-slate-500">{new Date(c.created_at).toLocaleDateString()}</span>
                    </div>
                  )) || <div className="text-slate-500 text-sm">No commits recorded</div>}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-slate-500">Loading Time Machine data...</div>
          )}
        </div>
      )}

      {/* TAB 4: WATCHTOWER LIVE */}
      {activeTab === 'watchtower' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Radio className="w-5 h-5 text-red-400 animate-pulse" />
                Watchtower Live Activity Stream
              </h2>
              <p className="text-xs text-slate-400">
                Real-time repository activity feed, scan events, finding detections, and release actions.
              </p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
              Live Polling (10s)
            </span>
          </div>

          <div className="space-y-2">
            {watchtowerEvents.length > 0 ? (
              watchtowerEvents.map((ev: any, idx: number) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start justify-between gap-4"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-brand-500/10 text-brand-400 border border-brand-500/20 mt-0.5">
                      <Activity className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-white capitalize">
                        {ev.event_type?.replace(/_/g, ' ')}
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">
                        {JSON.stringify(ev.payload || {})}
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-slate-500 whitespace-nowrap">
                    {new Date(ev.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))
            ) : (
              <div className="p-12 text-center text-slate-500 bg-slate-900/30 rounded-2xl border border-slate-800">
                No recent Watchtower events recorded yet.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: ISSUES & TASKS */}
      {activeTab === 'issues' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 space-y-4">
              <h2 className="text-lg font-bold text-white">Repository Issues & Tasks</h2>
              <div className="space-y-2">
                {issuesData.length > 0 ? (
                  issuesData.map((issue: any) => (
                    <div
                      key={issue.id}
                      className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                              issue.severity === 'Critical'
                                ? 'bg-red-500/10 text-red-400'
                                : 'bg-amber-500/10 text-amber-400'
                            }`}
                          >
                            {issue.severity}
                          </span>
                          <span className="text-sm font-semibold text-white">{issue.title}</span>
                        </div>
                        <p className="text-xs text-slate-400">{issue.description}</p>
                      </div>
                      <span className="text-xs px-2 py-1 rounded bg-slate-800 text-slate-300">
                        {issue.status}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center text-slate-500 bg-slate-900/30 rounded-xl border border-slate-800">
                    No active issue tasks. You can create one below.
                  </div>
                )}
              </div>

              {/* Create Issue Form */}
              <form onSubmit={handleCreateIssue} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
                <h3 className="text-sm font-semibold text-white">Create New Issue Task</h3>
                <input
                  type="text"
                  placeholder="Issue title"
                  value={newIssueTitle}
                  onChange={(e) => setNewIssueTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                  required
                />
                <textarea
                  placeholder="Description..."
                  value={newIssueDesc}
                  onChange={(e) => setNewIssueDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white h-20"
                />
                <div className="flex gap-3">
                  <select
                    value={newIssueSeverity}
                    onChange={(e) => setNewIssueSeverity(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                  >
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                    <option value="Critical">Critical</option>
                  </select>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-xs font-semibold"
                  >
                    Create Issue
                  </button>
                </div>
              </form>
            </div>

            {/* Ownership / Bus Factor */}
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-brand-400" />
                Ownership & Bus Factor
              </h2>
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
                <div className="text-xs text-slate-400">
                  Commit authorship distribution across recorded commits.
                </div>
                {ownershipData?.contributors?.map((c: any) => (
                  <div key={c.author} className="space-y-1">
                    <div className="flex justify-between text-xs text-slate-300">
                      <span>{c.author}</span>
                      <span className="font-semibold">{c.commits} commits</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-brand-500"
                        style={{ width: `${Math.min(100, c.commits * 10)}%` }}
                      />
                    </div>
                  </div>
                )) || <div className="text-xs text-slate-500">No author data available</div>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 6: PROJECT MEMORY (LIVING KNOWLEDGE BASE) */}
      {activeTab === 'memory' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-brand-400" />
                Project Memory & Knowledge Base
              </h2>
              <p className="text-xs text-slate-400">
                Preserve architecture decisions, onboarding guides, runbooks, and known hazards across sessions.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 space-y-4">
              {memories.length > 0 ? (
                memories.map((m: any) => (
                  <div
                    key={m.id}
                    className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3 relative group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-brand-500/10 text-brand-400 border border-brand-500/20 uppercase">
                          {m.category}
                        </span>
                        <h3 className="text-sm font-bold text-white">{m.title}</h3>
                      </div>
                      <button
                        onClick={() => handleDeleteMemory(m.id)}
                        className="text-slate-500 hover:text-red-400 transition"
                        title="Delete memory note"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="text-xs text-slate-300 whitespace-pre-wrap">{m.content}</p>
                    {m.tags && m.tags.length > 0 && (
                      <div className="flex gap-1.5 pt-2">
                        {m.tags.map((t: string) => (
                          <span
                            key={t}
                            className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400"
                          >
                            #{t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-12 text-center text-slate-500 bg-slate-900/30 rounded-2xl border border-slate-800">
                  No project memories recorded yet. Record architecture decisions or setup runbooks below.
                </div>
              )}
            </div>

            {/* Add Memory Form */}
            <form onSubmit={handleSaveMemory} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-brand-400" />
                Record Project Memory
              </h3>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Category</label>
                <select
                  value={newMemoryCategory}
                  onChange={(e) => setNewMemoryCategory(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                >
                  <option value="DECISION">Architecture Decision (ADR)</option>
                  <option value="RUNBOOK">Runbook / Procedure</option>
                  <option value="HAZARD">Known Hazard / Caveat</option>
                  <option value="ONBOARDING">Onboarding Note</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Title</label>
                <input
                  type="text"
                  placeholder="e.g. Migration strategy for auth tokens"
                  value={newMemoryTitle}
                  onChange={(e) => setNewMemoryTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Content</label>
                <textarea
                  placeholder="Detailed context, rationale, or instructions..."
                  value={newMemoryContent}
                  onChange={(e) => setNewMemoryContent(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white h-28"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  placeholder="auth, security, database"
                  value={newMemoryTags}
                  onChange={(e) => setNewMemoryTags(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>
              <button
                type="submit"
                className="w-full py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-xs font-semibold"
              >
                Save Knowledge
              </button>
            </form>
          </div>
        </div>
      )}

      {/* TAB 7: RELEASE READINESS */}
      {activeTab === 'releases' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 space-y-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Rocket className="w-5 h-5 text-brand-400" />
                Release Candidates & Audit History
              </h2>

              <div className="space-y-3">
                {releasesData.length > 0 ? (
                  releasesData.map((r: any) => (
                    <div
                      key={r.id}
                      className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-bold text-brand-400">
                            {r.version_tag}
                          </span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded font-semibold ${
                              r.status === 'READY'
                                ? 'bg-emerald-500/10 text-emerald-400'
                                : 'bg-amber-500/10 text-amber-400'
                            }`}
                          >
                            {r.status}
                          </span>
                        </div>
                        <span className="text-xs text-slate-400">
                          Readiness Score: <b className="text-white">{r.readiness_score}%</b>
                        </span>
                      </div>
                      <p className="text-xs text-slate-300">{r.release_notes}</p>
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center text-slate-500 bg-slate-900/30 rounded-xl border border-slate-800">
                    No release records created yet.
                  </div>
                )}
              </div>
            </div>

            {/* Prepare Release Form */}
            <form onSubmit={handlePrepareRelease} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
              <h3 className="text-sm font-bold text-white">Prepare Release Candidate</h3>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Version Tag</label>
                <input
                  type="text"
                  placeholder="v1.2.0"
                  value={releaseTag}
                  onChange={(e) => setReleaseTag(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white font-mono"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Release Notes</label>
                <textarea
                  placeholder="Summarize changes, features, and migrations..."
                  value={releaseNotes}
                  onChange={(e) => setReleaseNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white h-24"
                />
              </div>
              <button
                type="submit"
                className="w-full py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-xs font-semibold"
              >
                Evaluate & Prepare Release
              </button>
            </form>
          </div>
        </div>
      )}

      {/* TAB 8: AI EXPERT & FIX AGENT */}
      {activeTab === 'aiexpert' && (
        <div className="space-y-6">
          {/* AI Provider Telemetry & Diagnostics Panel */}
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    AI Provider Telemetry & Diagnostics
                    <button
                      onClick={() => {
                        setExplainerInitial('aiexpert');
                        setShowExplainer(true);
                      }}
                      className="text-slate-400 hover:text-brand-400 transition"
                      title="Learn about AI capabilities and boundaries"
                    >
                      <HelpCircle className="w-4 h-4" />
                    </button>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Truthful runtime status, active provider verification, automated secret scrubbing, and deterministic fallback.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {aiStatus?.execution_mode === 'real_provider' && (
                  <span className="text-xs px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Real AI Provider Active
                  </span>
                )}
                {aiStatus?.execution_mode === 'mock_provider' && (
                  <span className="text-xs px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-semibold flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5" />
                    Mock AI Provider Active
                  </span>
                )}
                {(!aiStatus || aiStatus?.execution_mode === 'deterministic_fallback') && (
                  <span className="text-xs px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5" />
                    Deterministic Fallback Mode
                  </span>
                )}

                <button
                  onClick={handleTestAiConnection}
                  disabled={aiTestingConnection}
                  className="flex items-center gap-2 px-3 py-1.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition shadow-sm"
                >
                  {aiTestingConnection ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Probing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      Test Connection
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Diagnostics Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 text-xs">
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                <span className="text-slate-500 text-[11px] block">Active Provider</span>
                <span className="font-semibold text-white capitalize mt-0.5 block">
                  {aiStatus?.active_provider || 'None'}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                <span className="text-slate-500 text-[11px] block">Model Identifier</span>
                <span className="font-mono text-slate-200 mt-0.5 block">
                  {aiStatus?.active_model || 'none'}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                <span className="text-slate-500 text-[11px] block">Secret Redaction</span>
                <span className="font-semibold text-emerald-400 mt-0.5 block flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Active (0 Leakage)
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                <span className="text-slate-500 text-[11px] block">LRU Cache Entries</span>
                <span className="font-semibold text-white mt-0.5 block">
                  {aiStatus?.cache_size ?? 0} cached items
                </span>
              </div>
            </div>

            {/* Status Message */}
            {aiStatus?.status_message && (
              <p className="text-xs text-slate-400 italic">
                Telemetry note: {aiStatus.status_message}
              </p>
            )}

            {/* Test Connection Banner */}
            {aiConnectionResult && (
              <div
                className={`p-3.5 rounded-xl text-xs flex items-center justify-between border ${
                  aiConnectionResult.success
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                    : 'bg-amber-500/10 border-amber-500/20 text-amber-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  {aiConnectionResult.success ? (
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  )}
                  <span>{aiConnectionResult.message}</span>
                </div>
                {aiConnectionResult.latency_ms > 0 && (
                  <span className="font-mono text-[11px] opacity-80">
                    {aiConnectionResult.latency_ms}ms
                  </span>
                )}
              </div>
            )}

            {/* Configuration Guide for Render */}
            {aiStatus?.execution_mode === 'deterministic_fallback' && (
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                <div className="font-semibold text-slate-300 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-brand-400" />
                  How to activate live LLM completion on Render:
                </div>
                <p>
                  Add <code className="text-brand-300 font-mono">GEMINI_API_KEY</code>,{' '}
                  <code className="text-brand-300 font-mono">OPENAI_API_KEY</code>, or{' '}
                  <code className="text-brand-300 font-mono">ANTHROPIC_API_KEY</code> in Render Dashboard &rarr; GitFlow Backend &rarr; Environment.
                  GitFlow auto-detects the provider and immediately enables live completion.
                </p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Ask Repository AI */}
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-brand-400" />
                  Ask Repository Expert
                </h3>
                <span className="text-[11px] text-slate-400">Contextual Q&A</span>
              </div>
              <form onSubmit={handleAskAi} className="space-y-3">
                <textarea
                  placeholder="e.g. How does authentication work in this repository? What are the main entry points?"
                  value={aiQuestion}
                  onChange={(e) => setAiQuestion(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-white h-24 focus:border-brand-500 outline-none"
                  required
                />
                <button
                  type="submit"
                  disabled={aiLoading}
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-2 transition"
                >
                  {aiLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  Ask Question
                </button>
              </form>

              {aiResponse && (
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 mt-4">
                  <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-800/80">
                    <span>Provider: <b className="text-white">{aiResponse.provider}</b></span>
                    <span>Model: <b className="text-white">{aiResponse.model}</b></span>
                  </div>
                  <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {aiResponse.answer}
                  </p>
                  {renderProvenanceBadge(aiResponse)}
                </div>
              )}
            </div>

            {/* Feature Completeness Checker */}
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <CheckSquare className="w-4 h-4 text-emerald-400" />
                  Feature Completeness Checker
                </h3>
                <span className="text-[11px] text-slate-400">Spec Verification</span>
              </div>
              <form onSubmit={handleCheckCompleteness} className="space-y-3">
                <textarea
                  placeholder="Enter acceptance criteria or feature spec to verify supporting code artifacts..."
                  value={completenessCriteria}
                  onChange={(e) => setCompletenessCriteria(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-white h-24 focus:border-brand-500 outline-none"
                  required
                />
                <button
                  type="submit"
                  disabled={completenessLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-2 transition"
                >
                  {completenessLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Verify Completeness
                </button>
              </form>

              {completenessResult && (
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 mt-4 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-emerald-400">
                      Status: {completenessResult.evaluation_status}
                    </span>
                  </div>
                  <p className="text-slate-300 leading-relaxed">{completenessResult.summary}</p>
                  {renderProvenanceBadge(completenessResult)}
                </div>
              )}
            </div>

            {/* Self-Validating Fix Agent */}
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4 md:col-span-2">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Wrench className="w-4 h-4 text-amber-400" />
                Self-Validating Fix Agent
              </h3>
              <p className="text-xs text-slate-400">
                Generates unified diff candidate patches for scanner findings with automated syntax and AST validation. Explicit user confirmation is strictly required prior to any mutation.
              </p>
              <form onSubmit={handleGenerateFixCandidate} className="flex gap-3">
                <input
                  type="number"
                  placeholder="Finding ID (e.g. 1)"
                  value={fixCandidateFindingId}
                  onChange={(e) => setFixCandidateFindingId(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white w-48"
                  required
                />
                <button
                  type="submit"
                  disabled={fixCandidateLoading}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-2 transition"
                >
                  {fixCandidateLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                  Generate Candidate Fix
                </button>
              </form>

              {fixCandidateResult && (
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 mt-4 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white">Target File: {fixCandidateResult.file_path}</span>
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-semibold uppercase">
                      Status: {fixCandidateResult.status}
                    </span>
                  </div>
                  {fixCandidateResult.diff && (
                    <pre className="p-3 bg-black/60 rounded-lg text-[11px] text-emerald-400 overflow-x-auto font-mono">
                      {fixCandidateResult.diff}
                    </pre>
                  )}
                  {renderProvenanceBadge(fixCandidateResult)}
                  <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-red-300 text-[11px]">
                    <b>Safety Policy:</b> Explicit user authorization is required before applying this patch to the repository working directory.
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 9: CROSS-REPO RADAR */}
      {activeTab === 'radar' && (
        <div className="space-y-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-brand-400" />
            Cross-Repository Change Radar
          </h2>
          <p className="text-xs text-slate-400">
            Mapping shared package dependencies, internal service APIs, and submodules across connected repositories.
          </p>

          {crossRepoData ? (
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="text-sm font-semibold text-white">
                Relationships for {crossRepoData.repo_name}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-xs uppercase font-semibold text-slate-400">Upstream Dependencies</span>
                  <div className="text-xl font-bold text-white mt-1">
                    {crossRepoData.upstream_dependencies?.length || 0}
                  </div>
                </div>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-xs uppercase font-semibold text-slate-400">Downstream Consumers</span>
                  <div className="text-xl font-bold text-white mt-1">
                    {crossRepoData.downstream_consumers?.length || 0}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-slate-500">Loading cross-repo relationships...</div>
          )}
        </div>
      )}

      {/* Interactive Feature Guide Modal */}
      <FeatureExplainerModal
        isOpen={showExplainer}
        onClose={() => setShowExplainer(false)}
        initialTabId={explainerInitial}
      />
    </div>
  );
}
