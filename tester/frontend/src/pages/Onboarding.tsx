import { useState, useEffect, useRef } from 'react';
import { GitBranch, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { apiClient } from '../config';
import { ScanningHUD } from '../components/ScanningHUD';

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [scanStatus, setScanStatus] = useState<string | null>(null);
  const [scannedSha, setScannedSha] = useState<string | null>(null);
  const [scanId, setScanId] = useState<number | null>(null);
  const [hudScore, setHudScore] = useState<number | null>(null);
  const [hudActionableCount, setHudActionableCount] = useState<number>(0);
  const [hudFixturesCount, setHudFixturesCount] = useState<number>(0);
  
  const [repoUrl, setRepoUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [repoId, setRepoId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  const pollingRef = useRef<any>(null);
  const consecutiveErrorsRef = useRef(0);
  const startPollingTimeRef = useRef<number>(0);

  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const fetchScanStatus = async (repository_id: number, currentScanId: number) => {
    try {
      const res = await apiClient.get(`/repositories/${repository_id}/scans/${currentScanId}`);
      consecutiveErrorsRef.current = 0;
      
      const status = res.data.status;
      setScanStatus(status);
      if (status === 'FAILED') {
        setErrorMsg(res.data.error_message || 'The scan failed without an additional message. Try again or contact support with the scan ID.');
      }
      if (res.data.commit_sha && res.data.commit_sha !== "HEAD") {
          setScannedSha(res.data.commit_sha.substring(0, 7));
      }

      if (status === 'COMPLETED' || status === 'PARTIAL') {
        try {
          const auditRes = await apiClient.get(`/repositories/${repository_id}/scans/${currentScanId}/audit`);
          const audit = auditRes.data;
          setHudScore(audit.risk_score);
          const actCount = (audit.findings || []).filter((f: any) => !f.is_test_fixture).length;
          const fixCount = (audit.findings || []).filter((f: any) => f.is_test_fixture).length;
          setHudActionableCount(actCount);
          setHudFixturesCount(fixCount);
        } catch {
          setHudScore(res.data.risk_score || 100);
        }
      }

      return status;
    } catch (err) {
      console.error("Failed to poll scan status", err);
      consecutiveErrorsRef.current += 1;
      
      if (consecutiveErrorsRef.current >= 5) {
        setScanStatus('POLLING_ERROR');
        setErrorMsg("Unable to retrieve scan status. The scan may still be running.");
        return 'POLLING_ERROR';
      }
      return null;
    }
  };

  const pollScanStatus = async (repository_id: number, currentScanId: number) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    
    consecutiveErrorsRef.current = 0;
    startPollingTimeRef.current = Date.now();
    
    // Initial fetch
    const initialStatus = await fetchScanStatus(repository_id, currentScanId);
    
    if (initialStatus === 'COMPLETED' || initialStatus === 'FAILED' || initialStatus === 'POLLING_ERROR') {
      return; // Do not create an interval
    }
    
    pollingRef.current = setInterval(async () => {
      if (Date.now() - startPollingTimeRef.current > 10 * 60 * 1000) {
        clearInterval(pollingRef.current);
        setScanStatus('TIMEOUT');
        setErrorMsg("Scan is taking longer than expected.");
        return;
      }
      
      const status = await fetchScanStatus(repository_id, currentScanId);
      if (status === 'COMPLETED' || status === 'FAILED' || status === 'POLLING_ERROR') {
        clearInterval(pollingRef.current);
      }
    }, 1500);
  };

  const handleAddRepository = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl) return;
    
    setIsSubmitting(true);
    setErrorMsg(null);
    
    try {
      // 1. Create/Add Repository
      const repoRes = await apiClient.post('/repositories/', { name: 'repo', url: repoUrl });
      const newRepoId = repoRes.data.id;
      setRepoId(newRepoId);
      
      // 2. Start initial scan
      const scanRes = await apiClient.post(`/repositories/${newRepoId}/scan`, { commit_sha: "HEAD" });
      const newScanId = scanRes.data.scan_id;
      setScanId(newScanId);
      
      // 3. Poll for status
      setStep(2);
      pollScanStatus(newRepoId, newScanId);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || "Failed to add repository. Please check the URL and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetryScan = async () => {
    if (!repoId) return;
    setScanStatus('QUEUED');
    setErrorMsg(null);
    setScannedSha(null);
    
    try {
      const scanRes = await apiClient.post(`/repositories/${repoId}/scan`, { commit_sha: "HEAD" });
      const newScanId = scanRes.data.scan_id;
      setScanId(newScanId);
      pollScanStatus(repoId, newScanId);
    } catch(e: any) {
      console.error("Failed to retry scan", e);
      setScanStatus('FAILED');
      setErrorMsg(e?.response?.data?.detail || "An error occurred while communicating with the server.");
    }
  };

  const steps = [
    { num: 1, title: 'Add Repository' },
    { num: 2, title: 'Initial Scan' }
  ];

  return (
    <div className="min-h-[calc(100vh-73px)] bg-background-light dark:bg-background-dark text-slate-900 dark:text-white pt-24">
      <div className="max-w-3xl mx-auto py-8">
        {/* Stepper */}
        <div className="mb-12">
          <div className="flex items-center justify-center space-x-8">
            {steps.map((s, i) => (
              <div key={s.num} className="flex flex-col items-center relative">
                {i !== 0 && (
                  <div className={`absolute top-5 -left-12 w-16 h-[2px] -translate-x-1/2 ${
                    step >= s.num ? 'bg-brand-500' : 'bg-border-light dark:bg-border-dark'
                  }`} />
                )}
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg border-2 z-10 transition-colors ${
                  step > s.num ? 'bg-brand-500 border-brand-500 text-white' : 
                  step === s.num ? 'bg-background-light dark:bg-background-dark border-brand-500 text-brand-500' :
                  'bg-surface-light dark:bg-surface-dark border-border-light dark:border-border-dark text-slate-400'
                }`}>
                  {step > s.num ? <CheckCircle2 className="w-5 h-5" /> : s.num}
                </div>
                <span className={`mt-2 text-sm font-medium ${step >= s.num ? 'text-slate-900 dark:text-white' : 'text-slate-400'}`}>
                  {s.title}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-xl shadow-soft dark:shadow-soft-dark overflow-hidden">
          {step === 1 && (
            <div className="p-12">
              <div className="flex flex-col items-center text-center mb-10">
                <div className="w-20 h-20 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-6">
                  <GitBranch className="w-10 h-10 text-slate-700 dark:text-slate-300" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Connect a GitHub Repository</h2>
                <p className="text-slate-500 dark:text-slate-400 max-w-md">
                  Enter a GitHub repository URL to create its Risk Passport and monitor new commits. Private repositories require a GitHub account with access.
                </p>
              </div>

              {errorMsg && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg mb-6 flex items-center text-left">
                  <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
                  <p>{errorMsg}</p>
                </div>
              )}

              <form onSubmit={handleAddRepository} className="max-w-lg mx-auto">
                <div className="mb-6">
                  <label htmlFor="repoUrl" className="block text-sm font-medium mb-2 text-left text-slate-700 dark:text-slate-300">
                    GitHub Repository URL
                  </label>
                  <input
                    id="repoUrl"
                    type="url"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    placeholder="https://github.com/owner/repository"
                    className="w-full px-4 py-3 rounded-lg bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all"
                    required
                  />
                </div>
                <button 
                  type="submit"
                  disabled={isSubmitting || !repoUrl}
                  className="w-full py-3 bg-brand-500 text-white font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {isSubmitting ? (
                    <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Adding Repository...</>
                  ) : "Add Repository"}
                </button>
              </form>
            </div>
          )}

          {step === 2 && (
            <ScanningHUD
              isOpen={true}
              repoName={repoUrl.replace(/^https?:\/\/github\.com\//, '') || 'Repository'}
              commitSha={scannedSha || 'HEAD'}
              scanStatus={scanStatus}
              scanId={scanId}
              riskScore={hudScore}
              actionableFindingsCount={hudActionableCount}
              fixturesCount={hudFixturesCount}
              errorMessage={errorMsg}
              onClose={() => { window.location.href = '/dashboard'; }}
              onViewAudit={(sId) => { window.location.href = `/repositories/${repoId}/scans/${sId}/audit`; }}
              onDownloadPdf={(sId) => { window.open(`${apiClient.defaults.baseURL}/repositories/${repoId}/scans/${sId}/report.pdf`, '_blank'); }}
              onRetry={handleRetryScan}
            />
          )}
        </div>
      </div>
    </div>
  );
}
