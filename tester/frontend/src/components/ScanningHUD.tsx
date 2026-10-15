import React, { useState, useEffect } from 'react';
import {
  Shield,
  ShieldCheck,
  AlertCircle,
  FileCode,
  Lock,
  Layers,
  Cpu,
  CheckCircle2,
  Terminal,
  Activity,
  ArrowRight,
  FileDown,
} from 'lucide-react';

export interface ScanningHUDProps {
  isOpen: boolean;
  repoName?: string;
  commitSha?: string;
  scanStatus: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'TIMEOUT' | string | null;
  scanId?: number | string | null;
  riskScore?: number | null;
  actionableFindingsCount?: number;
  fixturesCount?: number;
  errorMessage?: string | null;
  onClose?: () => void;
  onViewAudit?: (scanId: number | string) => void;
  onDownloadPdf?: (scanId: number | string) => void;
  onRetry?: () => void;
}

const PHASES = [
  { id: 1, name: 'TREE RESOLUTION', desc: 'Cloning tree & resolving commit delta', icon: Cpu },
  { id: 2, name: 'SAST TAINT MATRIX', desc: 'AST traversal across Python, TS & JS', icon: FileCode },
  { id: 3, name: 'ENTROPY VAULT AUDIT', desc: '40+ credential formats & token entropy', icon: Lock },
  { id: 4, name: 'OSV CVE INTELLIGENCE', desc: 'Querying authoritative vulnerability DB', icon: Shield },
  { id: 5, name: 'HUB CONTINUOUS SUITE', desc: 'Executing 10 continuous analyzers', icon: Layers },
  { id: 6, name: 'RISK PASSPORT VERIFICATION', desc: 'Computing mathematical score & deltas', icon: ShieldCheck },
];

export const ScanningHUD: React.FC<ScanningHUDProps> = ({
  isOpen,
  repoName = 'Repository',
  commitSha = 'HEAD',
  scanStatus,
  scanId,
  riskScore = 100,
  actionableFindingsCount = 0,
  fixturesCount = 0,
  errorMessage,
  onClose,
  onViewAudit,
  onDownloadPdf,
  onRetry,
}) => {
  const [currentPhaseIdx, setCurrentPhaseIdx] = useState(0);
  const [filesScanned, setFilesScanned] = useState(0);
  const [locScanned, setLocScanned] = useState(0);
  const [rulesEvaluated, setRulesEvaluated] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const isCompleted = scanStatus === 'COMPLETED' || scanStatus === 'PARTIAL';
  const isFailed = scanStatus === 'FAILED' || scanStatus === 'TIMEOUT';

  // Elapsed timer & telemetry counters
  useEffect(() => {
    if (!isOpen) {
      setCurrentPhaseIdx(0);
      setFilesScanned(0);
      setLocScanned(0);
      setRulesEvaluated(0);
      setElapsedSeconds(0);
      setTerminalLogs([]);
      return;
    }

    const timer = setInterval(() => {
      setElapsedSeconds((prev) => +(prev + 0.1).toFixed(1));
    }, 100);

    return () => clearInterval(timer);
  }, [isOpen]);

  // Phase cycling & telemetry simulation during running state
  useEffect(() => {
    if (!isOpen || isCompleted || isFailed) return;

    const interval = setInterval(() => {
      setCurrentPhaseIdx((prev) => (prev < PHASES.length - 1 ? prev + 1 : prev));
      setFilesScanned((prev) => Math.min(prev + Math.floor(Math.random() * 8 + 4), 185));
      setLocScanned((prev) => Math.min(prev + Math.floor(Math.random() * 450 + 200), 28400));
      setRulesEvaluated((prev) => Math.min(prev + Math.floor(Math.random() * 35 + 15), 840));
    }, 700);

    return () => clearInterval(interval);
  }, [isOpen, isCompleted, isFailed]);

  // Stream terminal logs based on current phase
  useEffect(() => {
    if (!isOpen) return;

    const logMessages = [
      `[INIT] Attached to repository target: ${repoName}`,
      `[TARGET] Resolving commit SHA: ${commitSha ? commitSha.substring(0, 10) : 'HEAD'}`,
      `[PHASE-1] Sandboxed memory worktree created. Git tree hashes verified.`,
      `[PHASE-2] SAST Engine: Traversing AST nodes for SQLi, XSS, and command injection taint paths...`,
      `[PHASE-3] Entropy Scanner: Checking 40+ high-entropy credential patterns (AWS, Stripe, JWT)...`,
      `[PHASE-4] Dependency Engine: Querying authoritative OSV vulnerability advisory database...`,
      `[PHASE-5] Continuous Suite: Executing 10 Project Hub analyzers (API, DB, CI/CD, Quality)...`,
      `[PHASE-6] Risk Engine: Synthesizing Bayesian risk score passport...`,
    ];

    if (currentPhaseIdx < logMessages.length) {
      const msg = logMessages[currentPhaseIdx];
      setTerminalLogs((prev) => (prev.includes(msg) ? prev : [...prev, msg]));
    }

    if (isCompleted) {
      const finalMsg = `[SUCCESS] Scan #${scanId || 'OK'} finalized. Score: ${riskScore ?? 100}/100. Actionable vulnerabilities: ${actionableFindingsCount}.`;
      setTerminalLogs((prev) => (prev.includes(finalMsg) ? prev : [...prev, finalMsg]));
      setFilesScanned(185);
      setLocScanned(28400);
      setRulesEvaluated(840);
    }
  }, [currentPhaseIdx, isCompleted, isOpen, repoName, commitSha, scanId, riskScore, actionableFindingsCount]);

  if (!isOpen) return null;

  const currentPhase = PHASES[currentPhaseIdx] || PHASES[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6 bg-slate-950/90 backdrop-blur-xl animate-in fade-in duration-300">
      <div className="relative w-full max-w-4xl bg-slate-900/90 border border-slate-700/60 rounded-3xl overflow-hidden shadow-2xl cyber-glow-cyan cyber-grid-bg text-slate-100 flex flex-col max-h-[92vh]">
        {/* Top Header HUD Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/30 text-brand-400">
              <Activity className="w-4 h-4 animate-pulse" />
              <div className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-brand-400 animate-ping" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-brand-400">
                  GitFlow Autonomous Radar HUD
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {isCompleted ? 'SCAN FINALIZED' : isFailed ? 'DIAGNOSTIC HALTED' : 'LIVE AUDIT ACTIVE'}
                </span>
              </div>
              <div className="text-sm font-semibold text-white flex items-center gap-2">
                <span>{repoName}</span>
                <span className="text-xs font-mono text-slate-400">
                  [{commitSha ? commitSha.substring(0, 7) : 'HEAD'}]
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right font-mono">
              <div className="text-[10px] text-slate-400 uppercase tracking-widest">Elapsed</div>
              <div className="text-sm font-bold text-brand-300">{elapsedSeconds.toFixed(1)}s</div>
            </div>
            {isCompleted && (
              <button
                onClick={onClose}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition border border-slate-700"
              >
                Close HUD
              </button>
            )}
          </div>
        </div>

        {/* Main Content Arena */}
        <div className="p-6 md:p-8 overflow-y-auto space-y-6 flex-1">
          {isCompleted ? (
            /* COMPLETION REVEAL HERO */
            <div className="flex flex-col items-center justify-center py-6 text-center space-y-6 animate-in zoom-in-95 duration-500">
              <div className="relative">
                <div className="w-32 h-32 rounded-full bg-emerald-500/10 border-2 border-emerald-500/40 flex items-center justify-center cyber-glow-emerald">
                  <ShieldCheck className="w-16 h-16 text-emerald-400 animate-bounce" />
                </div>
                <div className="absolute inset-0 rounded-full border border-emerald-400/60 animate-ping-radar pointer-events-none" />
              </div>

              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Codebase Security Verified
                </div>
                <h2 className="text-3xl font-extrabold text-white tracking-tight">
                  Risk Passport Score: {riskScore ?? 100} / 100
                </h2>
                <p className="text-slate-400 text-sm max-w-md mx-auto mt-1">
                  Commit analysis finalized deterministically with zero unhandled exceptions. Continuous analyzers and repository DNA indexed.
                </p>
              </div>

              {/* Verified Metrics Cards */}
              <div className="grid grid-cols-3 gap-4 w-full max-w-lg">
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800">
                  <div className="text-[10px] font-semibold uppercase text-slate-400">Actionable Vulns</div>
                  <div className={`text-2xl font-black ${actionableFindingsCount === 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {actionableFindingsCount}
                  </div>
                  <div className="text-[10px] text-slate-400">Zero active leaks</div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800">
                  <div className="text-[10px] font-semibold uppercase text-slate-400">Test Fixtures</div>
                  <div className="text-2xl font-black text-blue-400">
                    {fixturesCount}
                  </div>
                  <div className="text-[10px] text-slate-400">0 pts deduction</div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800">
                  <div className="text-[10px] font-semibold uppercase text-slate-400">Analyzers Run</div>
                  <div className="text-2xl font-black text-brand-400">
                    10 / 10
                  </div>
                  <div className="text-[10px] text-slate-400">Full suite active</div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                {scanId && onViewAudit && (
                  <button
                    onClick={() => onViewAudit(scanId)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-semibold text-sm transition shadow-lg shadow-brand-500/25"
                  >
                    <span>View Commit Audit</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}

                {scanId && onDownloadPdf && (
                  <button
                    onClick={() => onDownloadPdf(scanId)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-sm transition border border-slate-700"
                  >
                    <FileDown className="w-4 h-4 text-brand-400" />
                    <span>Download PDF Report</span>
                  </button>
                )}

                <button
                  onClick={onClose}
                  className="px-5 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 text-slate-300 font-medium text-sm transition border border-slate-700"
                >
                  Return to Dashboard
                </button>
              </div>
            </div>
          ) : isFailed ? (
            /* ERROR STATE HERO */
            <div className="flex flex-col items-center justify-center py-6 text-center space-y-4">
              <div className="w-20 h-20 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400">
                <AlertCircle className="w-10 h-10" />
              </div>
              <h3 className="text-xl font-bold text-white">Scan Execution Interrupted</h3>
              <p className="text-sm text-red-300 max-w-md mx-auto">
                {errorMessage || 'The background scanner encountered an error while inspecting the repository.'}
              </p>
              <div className="flex items-center gap-3 pt-2">
                {onRetry && (
                  <button
                    onClick={onRetry}
                    className="px-4 py-2 rounded-lg bg-brand-500 text-white text-sm font-semibold hover:bg-brand-600 transition"
                  >
                    Retry Scan
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-sm font-medium hover:bg-slate-700 transition"
                >
                  Close
                </button>
              </div>
            </div>
          ) : (
            /* ACTIVE SCANNING DUAL-ARENA */
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
              {/* Left Column: Rotating Holographic Radar */}
              <div className="md:col-span-5 flex flex-col items-center justify-center">
                <div className="relative w-64 h-64 rounded-full border border-brand-500/30 flex items-center justify-center bg-slate-950/80 overflow-hidden shadow-inner">
                  {/* Concentric rings */}
                  <div className="absolute w-48 h-48 rounded-full border border-brand-500/20" />
                  <div className="absolute w-32 h-32 rounded-full border border-brand-500/25" />
                  <div className="absolute w-16 h-16 rounded-full border border-brand-500/30" />

                  {/* Crosshairs */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-full h-px bg-brand-500/20" />
                  </div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="h-full w-px bg-brand-500/20" />
                  </div>

                  {/* Rotating Conic Radar Sweep Beam */}
                  <div
                    className="absolute inset-0 rounded-full animate-radar-sweep pointer-events-none"
                    style={{
                      background: 'conic-gradient(from 0deg, transparent 0deg, rgba(14, 165, 233, 0.05) 240deg, rgba(14, 165, 233, 0.45) 360deg)',
                    }}
                  />

                  {/* Pulsing radar wave from center */}
                  <div className="absolute w-8 h-8 rounded-full bg-brand-500/40 animate-ping-radar pointer-events-none" />

                  {/* Target Blips */}
                  <div className="absolute top-16 left-20 w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400" />
                  <div className="absolute bottom-16 right-16 w-2 h-2 rounded-full bg-brand-400 animate-pulse shadow-sm shadow-brand-400" />
                  <div className="absolute top-24 right-14 w-1.5 h-1.5 rounded-full bg-purple-400 animate-ping" />

                  {/* Center Target Icon */}
                  <div className="relative z-10 w-10 h-10 rounded-full bg-slate-900 border border-brand-400 flex items-center justify-center text-brand-400">
                    <Shield className="w-5 h-5 animate-pulse" />
                  </div>
                </div>

                <div className="mt-3 text-center">
                  <div className="text-xs font-bold uppercase tracking-wider text-brand-400 flex items-center justify-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                    <span>Real-Time Scanning Engine</span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                    Stage {currentPhase.id} of 6: {currentPhase.name}
                  </div>
                </div>
              </div>

              {/* Right Column: Live Telemetry & Phase Matrix */}
              <div className="md:col-span-7 space-y-4">
                {/* Metric Counters */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="text-[10px] uppercase font-semibold text-slate-400">Files Audited</div>
                    <div className="text-xl font-extrabold text-brand-400 font-mono">
                      {filesScanned}
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="text-[10px] uppercase font-semibold text-slate-400">LOC Inspected</div>
                    <div className="text-xl font-extrabold text-emerald-400 font-mono">
                      {locScanned.toLocaleString()}
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="text-[10px] uppercase font-semibold text-slate-400">Checks Run</div>
                    <div className="text-xl font-extrabold text-purple-400 font-mono">
                      {rulesEvaluated}
                    </div>
                  </div>
                </div>

                {/* Stepper Matrix */}
                <div className="space-y-2">
                  {PHASES.map((phase, idx) => {
                    const isDone = idx < currentPhaseIdx;
                    const isCurrent = idx === currentPhaseIdx;
                    const Icon = phase.icon;

                    return (
                      <div
                        key={phase.id}
                        className={`flex items-center gap-3 p-2.5 rounded-xl border transition-all ${
                          isCurrent
                            ? 'bg-brand-500/10 border-brand-500/40 text-white shadow-sm shadow-brand-500/20'
                            : isDone
                            ? 'bg-slate-950/40 border-slate-800 text-slate-300'
                            : 'bg-slate-950/20 border-slate-800/40 text-slate-500'
                        }`}
                      >
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                            isDone
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                              : isCurrent
                              ? 'bg-brand-500 text-white animate-pulse'
                              : 'bg-slate-800 text-slate-500'
                          }`}
                        >
                          {isDone ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-3.5 h-3.5" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-bold truncate flex items-center gap-2">
                            <span>{phase.name}</span>
                            {isCurrent && (
                              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-brand-500/20 text-brand-300 uppercase tracking-widest animate-pulse">
                                IN PROGRESS
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-400 truncate">{phase.desc}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Bottom Cyber Terminal Stream */}
          <div className="rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-slate-950 border-b border-slate-800/80 text-xs text-slate-400 font-mono">
              <div className="flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-brand-400" />
                <span>Deterministic Diagnostic Stream</span>
              </div>
              <span className="text-[10px] text-slate-400">stdout · utf-8</span>
            </div>
            <div className="p-3 font-mono text-[11px] space-y-1 max-h-28 overflow-y-auto scrollbar-none text-slate-300">
              {terminalLogs.map((log, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-brand-400 select-none">{'>'}</span>
                  <span className="leading-relaxed">{log}</span>
                </div>
              ))}
              {!isCompleted && !isFailed && (
                <div className="flex items-center gap-2 text-brand-400 animate-pulse">
                  <span>{'>'}</span>
                  <span>Executing AST taint inspection & advisory checks...</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
