import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { 
  FileText, 
  Upload, 
  Terminal, 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Zap, 
  Sparkles, 
  Copy, 
  Check, 
  Download, 
  RefreshCw, 
  Cpu, 
  Layers,
  Search,
  CheckCircle2,
  FileCode
} from 'lucide-react';

function ManualAnalysis() {
  const [logText, setLogText] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [aiFix, setAiFix] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [promptStyle, setPromptStyle] = useState('standard');
  const [copied, setCopied] = useState(false);
  const [isSolution, setIsSolution] = useState(false);
  const [copiedFindingIdx, setCopiedFindingIdx] = useState(null);
  const [fileName, setFileName] = useState('');

  // Scanning simulation steps for ultra-sleek HUD feedback
  useEffect(() => {
    let interval;
    if (loading) {
      setScanStep(0);
      interval = setInterval(() => {
        setScanStep(prev => (prev < 2 ? prev + 1 : prev));
      }, 500);
    } else {
      setScanStep(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const analyzeLog = async () => {
    if (!logText.trim()) return;
    setLoading(true);
    setAiFix(null);
    try {
      const response = await fetch('https://software-testing-teq9.onrender.com/runs/analyze-manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ log_text: logText })
      });
      const data = await response.json();
      setAnalysis(data);
    } catch (e) {
      console.error(e);
      alert("Analysis failed to connect to backend");
    }
    setLoading(false);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setFileName(file.name);

    if (file.name.endsWith(".zip")) {
      try {
        setLogText("⚡ High-speed unzipping in progress...");
        const { unzip } = await import("fflate");
        const buffer = new Uint8Array(await file.arrayBuffer());

        const unzipped = await new Promise((resolve, reject) => {
          unzip(
            buffer,
            {
              filter(entry) {
                const name = entry.name.toLowerCase();
                if (
                  name.includes("node_modules/") ||
                  name.includes(".git/") ||
                  name.includes(".next/") ||
                  name.includes("dist/") ||
                  name.includes("build/")
                ) {
                  return false;
                }
                if (
                  name.match(/\.(png|jpg|jpeg|gif|ico|svg|pdf|exe|dll|zip|tar|gz|7z|rar|mp4|webm|mp3|wav|woff|woff2|ttf|eot|otf|bin|iso|dmg|apk|jar|class|pyc|so|dylib|map|lock)$/i)
                ) {
                  return false;
                }
                return true;
              }
            },
            (err, data) => {
              if (err) reject(err);
              else resolve(data);
            }
          );
        });

        let extractedText = "";
        const decoder = new TextDecoder("utf-8", { fatal: false });

        for (const [filename, u8] of Object.entries(unzipped)) {
          if (!u8 || u8.length === 0) continue;
          try {
            const text = decoder.decode(u8);
            extractedText += `\n--- File: ${filename} ---\n` + text;
            if (extractedText.length > 500000) {
              extractedText += "\n... [TRUNCATED - LOG CONTENT REACHED SAFETY LIMIT] ...\n";
              break;
            }
          } catch (e) {
            console.warn("Skipping file:", filename);
          }
        }

        if (!extractedText.trim()) {
          setLogText("No text or log files were found in this zip!");
        } else {
          setLogText(extractedText.trim());
        }
      } catch (err) {
        console.error("Error unzipping file:", err);
        alert("Failed to unzip file. Make sure it is a valid zip archive.");
        setLogText("");
      }
    } else {
      const reader = new FileReader();
      reader.onload = (event) => {
        setLogText(event.target.result);
      };
      reader.readAsText(file);
    }
  };

  const exportPDF = () => {
    if (!analysis) return;
    const doc = new jsPDF();
    doc.setFontSize(18);
    doc.text("SecRunner Manual Log Analysis", 14, 22);
    doc.setFontSize(12);
    doc.text(`Overall Status: ${analysis.status}`, 14, 32);
    
    const tableData = analysis.findings.map(f => [
      f.severity,
      f.message,
      f.recommendation || ''
    ]);

    autoTable(doc, {
      startY: 40,
      head: [['Severity', 'Finding', 'Recommendation']],
      body: tableData,
      theme: 'grid',
      headStyles: { fillColor: [31, 41, 55] }
    });

    doc.save('sec-runner-analysis.pdf');
  };

  const buildPrompt = () => {
    if (!analysis) return "";
    let errorList = "";
    analysis.findings.forEach(f => {
      errorList += `File: ${f.message}\nSeverity: ${f.severity}\nRecommendation: ${f.recommendation || 'N/A'}\n\n`;
    });

    if (promptStyle === "advanced") {
      return `You are a senior full-stack software engineer and debugging specialist.

I have a codebase that is producing the following security and runtime issues:

**Error List:**
${errorList}
Your task is to inspect the entire codebase and identify the exact root cause, then provide the exact code changes required to fix it.

### GOAL
Fix these errors completely. Do NOT give generic suggestions. First inspect the actual project structure, routes, server configuration, and logic.

### STEP 1 — Find the Exact Root Cause
Determine exactly why the application is returning these errors. Do not stop at the first suspicious line. Trace the complete request.

### STEP 2 — Identify the Broken Code
Show the exact file and line/function responsible.

### STEP 3 — Provide the Exact Fix
Provide the complete corrected code. Do not provide pseudocode. Use the actual paths and framework conventions.

### STEP 4 — Final Response Format
Return your findings in this exact structure:
# Error Diagnosis
## 1. Root Cause
## 2. Broken File
## 3. Problematic Code
## 4. Corrected Code
## 5. Why This Fix Works

### STEP 5 — Check Related Files
After fixing the primary problem, inspect related code for additional causes.

### STEP 6 — Test the Fix
Explain exactly how to verify the fix. Provide commands appropriate for the actual project.

### STEP 7 — Check for Other Problems
Search the codebase for other broken file references or routes.`;
    } else {
      return `I have the following security issues and errors in my codebase that I need help fixing:

${errorList}
Please provide the exact code and configuration changes required to fix each of these issues. Format your response clearly in Markdown with code blocks and explanations.`;
    }
  };

  const generatePrompt = () => {
    if (!analysis) return;
    const prompt = buildPrompt();
    setAiFix(prompt);
    setIsSolution(false);
  };

  const solveWithGemini = async () => {
    if (!analysis) return;
    const prompt = aiFix && !isSolution ? aiFix : buildPrompt();

    setAiLoading(true);
    setAiFix("Contacting Gemini AI Co-Pilot... Please wait...");
    try {
      const response = await fetch('https://software-testing-teq9.onrender.com/runs/generate-fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ custom_prompt: prompt, findings: analysis.findings })
      });
      const data = await response.json();

      const aiResponseText = data.response || "No response from AI.";
      setAiFix(aiResponseText);
      setIsSolution(true);

      if (aiResponseText.includes("Gemini API Error") || aiResponseText.includes("Quota") || aiResponseText.includes("No valid Gemini API key") || aiResponseText.includes("Failed to contact")) {
        alert("⚠️ Gemini API Limit Reached or Missing!\n\nPlease add a new Gemini API Key to your backend to continue using the AI Co-Pilot.");
      }
    } catch (e) {
      console.error(e);
      setAiFix("Failed to connect to the backend AI engine.");
      alert("⚠️ Backend Error! Could not connect to the API.");
    }
    setAiLoading(false);
  };

  const copyToClipboard = () => {
    if (!aiFix) return;
    navigator.clipboard.writeText(aiFix);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyFindingText = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedFindingIdx(idx);
    setTimeout(() => setCopiedFindingIdx(null), 1800);
  };

  const criticalCount = analysis?.findings?.filter(f => f.severity.toLowerCase().includes('crit')).length || 0;
  const warningCount = analysis?.findings?.filter(f => f.severity.toLowerCase().includes('warn') || f.severity.toLowerCase().includes('med')).length || 0;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }} 
      animate={{ opacity: 1, y: 0 }} 
      transition={{ duration: 0.4 }}
      className="p-4 md:p-8 w-full h-full overflow-y-auto space-y-6"
    >
      
      {/* Animated Top Header HUD */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-cyan-accent/20">
        <div>
          <div className="flex items-center gap-3">
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ repeat: Infinity, duration: 20, ease: "linear" }}
              className="p-2 rounded-xl bg-cyan-accent/10 border border-cyan-accent/40 shadow-[0_0_15px_rgba(0,229,255,0.3)]"
            >
              <Cpu className="w-6 h-6 text-cyan-accent" />
            </motion.div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-wide flex items-center gap-3">
              Forensics Log Analyzer
            </h1>
          </div>
          <p className="text-gray-400 text-sm mt-1">
            Automated AST parser, vulnerability forensics, and multi-model AI Co-Pilot resolution.
          </p>
        </div>

        {/* Live Cyber Indicator Badge */}
        <div className="flex items-center gap-3">
          <motion.div 
            animate={{ boxShadow: ['0 0 10px rgba(0,229,255,0.2)', '0 0 20px rgba(0,229,255,0.6)', '0 0 10px rgba(0,229,255,0.2)'] }}
            transition={{ repeat: Infinity, duration: 2 }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/60 border border-cyan-accent/40 text-xs font-mono text-cyan-accent font-bold"
          >
            <span className="w-2 h-2 rounded-full bg-cyan-accent animate-ping" />
            LIVE AST ENGINE
          </motion.div>

          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-navy-panel border border-gray-800 text-xs font-mono text-gray-400">
            <Zap className="w-3.5 h-3.5 text-warn-amber" />
            fflate native v0.8
          </div>
        </div>
      </div>

      {/* Main Textarea with Laser Scan Animation */}
      <motion.div 
        layout
        className="relative rounded-2xl overflow-hidden border border-cyan-accent/30 bg-black/50 shadow-[inset_0_0_25px_rgba(0,0,0,0.9)] transition-colors focus-within:border-cyan-accent"
      >
        {/* Animated Laser Scanning Line */}
        {loading && (
          <motion.div 
            initial={{ top: '0%' }}
            animate={{ top: ['0%', '98%', '0%'] }}
            transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}
            className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-cyan-accent to-transparent shadow-[0_0_20px_#00e5ff] z-20 pointer-events-none"
          />
        )}

        {/* HUD Scanner Overlay when Loading */}
        <AnimatePresence>
          {loading && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-navy-bg/85 backdrop-blur-sm z-10 flex flex-col items-center justify-center gap-4 text-center p-6"
            >
              <div className="relative">
                <motion.div 
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                  className="w-16 h-16 rounded-full border-4 border-cyan-accent/20 border-t-cyan-accent shadow-[0_0_25px_rgba(0,229,255,0.5)]"
                />
                <Search className="w-6 h-6 text-cyan-accent absolute inset-0 m-auto animate-pulse" />
              </div>

              <div>
                <motion.div 
                  key={scanStep}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-cyan-accent font-mono text-sm font-bold tracking-wider uppercase"
                >
                  {scanStep === 0 && "[1/3] Parsing syntax AST tokens..."}
                  {scanStep === 1 && "[2/3] Auditing secret tokens & vulnerabilities..."}
                  {scanStep === 2 && "[3/3] Synthesizing comprehensive AI recommendations..."}
                </motion.div>
                <p className="text-gray-400 text-xs font-mono mt-1">Executing deep static pattern matching</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <textarea
          className="w-full h-64 p-5 bg-transparent text-cyan-accent font-mono text-sm outline-none resize-y placeholder:text-gray-600 leading-relaxed selection:bg-cyan-accent/20"
          placeholder="Paste your raw command output, compiler errors, or terminal logs here..."
          value={logText}
          onChange={(e) => setLogText(e.target.value)}
        />

        {/* Textarea Bottom Quick Bar */}
        <div className="px-5 py-2.5 bg-black/60 border-t border-cyan-accent/10 flex flex-wrap items-center justify-between text-xs font-mono text-gray-500">
          <div className="flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-cyan-accent" />
            <span>{logText ? `${logText.split('\n').length} lines loaded` : 'Buffer empty'}</span>
          </div>
          {fileName && (
            <span className="text-cyan-accent font-bold truncate max-w-xs">
              File: {fileName}
            </span>
          )}
        </div>
      </motion.div>

      {/* Interactive Upload & Drag-and-Drop Area */}
      <motion.div 
        whileHover={{ scale: 1.01, borderColor: 'rgba(0,229,255,0.4)' }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="bg-navy-panel p-5 rounded-xl border border-cyan-accent/20 shadow-lg relative flex flex-col md:flex-row items-center justify-between gap-4"
      >
        <div className="flex items-center gap-4">
          <motion.div 
            animate={{ y: [-2, 2, -2] }}
            transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
            className="p-3 rounded-xl bg-cyan-accent/10 border border-cyan-accent/30 text-cyan-accent shrink-0"
          >
            <Upload className="w-6 h-6" />
          </motion.div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Upload Log File or ZIP Archive
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Supports <span className="text-cyan-accent">.txt, .log, .out, .zip</span> (unpacked at hardware speeds via fflate)
            </p>
          </div>
        </div>

        <label className="cursor-pointer px-6 py-2.5 rounded-lg bg-cyan-accent/10 hover:bg-cyan-accent text-cyan-accent hover:text-navy-bg border border-cyan-accent/40 font-mono text-xs font-bold uppercase tracking-wider transition-all shadow-[0_0_12px_rgba(0,229,255,0.2)] hover:shadow-[0_0_20px_rgba(0,229,255,0.6)]">
          <span>Choose File</span>
          <input 
            type="file" 
            accept=".txt,.log,.out,.zip" 
            onChange={handleFileUpload} 
            className="hidden"
          />
        </label>
      </motion.div>

      {/* Action Controls Bar */}
      <div className="flex flex-wrap items-center gap-4 bg-navy-panel p-4 rounded-xl border border-cyan-accent/20">
        <motion.button 
          whileHover={{ scale: 1.03, boxShadow: '0 0 25px rgba(0,229,255,0.6)' }}
          whileTap={{ scale: 0.97 }}
          onClick={analyzeLog}
          disabled={loading || !logText.trim()}
          className="bg-cyan-accent text-navy-bg px-7 py-3 rounded-lg font-bold shadow-[0_0_15px_rgba(0,229,255,0.4)] hover:bg-white uppercase tracking-widest transition-all disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" /> Analyzing Logs...
            </>
          ) : (
            <>
              <Search className="w-4 h-4" /> Analyze Logs
            </>
          )}
        </motion.button>

        {analysis && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-wrap items-center gap-4 md:border-l md:pl-4 border-cyan-accent/20"
          >
            <motion.button 
              whileHover={{ scale: 1.03, borderColor: '#00e5ff' }}
              whileTap={{ scale: 0.97 }}
              onClick={exportPDF}
              className="bg-navy-bg border border-cyan-accent text-cyan-accent px-5 py-3 rounded-lg font-bold hover:bg-cyan-accent hover:text-navy-bg uppercase tracking-widest transition flex items-center gap-2 text-xs"
            >
              <Download className="w-4 h-4" /> Export PDF
            </motion.button>

            <div className="flex flex-col">
              <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">
                AI Prompt Style
              </label>
              <select 
                value={promptStyle} 
                onChange={e => setPromptStyle(e.target.value)}
                className="bg-black text-cyan-accent p-2 border border-cyan-accent/50 rounded-lg text-xs outline-none mt-1 font-mono"
              >
                <option value="standard">Standard Quick Fix</option>
                <option value="advanced">Senior Engineer (Advanced)</option>
              </select>
            </div>

            <motion.button 
              whileHover={{ scale: 1.03, boxShadow: '0 0 25px rgba(255,171,0,0.6)' }}
              whileTap={{ scale: 0.97 }}
              onClick={generatePrompt}
              disabled={aiLoading}
              className="bg-warn-amber text-navy-bg px-5 py-3 rounded-lg font-bold shadow-[0_0_15px_rgba(255,171,0,0.4)] hover:bg-white uppercase tracking-widest transition flex items-center gap-2 text-xs"
            >
              <Sparkles className="w-4 h-4" /> Generate AI Prompt
            </motion.button>
          </motion.div>
        )}
      </div>

      {/* AI Co-Pilot Resolution Prompt Section */}
      <AnimatePresence>
        {aiFix && (
          <motion.div 
            initial={{ opacity: 0, y: 15, scale: 0.98 }} 
            animate={{ opacity: 1, y: 0, scale: 1 }} 
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            className="bg-black p-6 rounded-xl shadow-2xl border border-warn-amber/50 relative overflow-hidden"
          >
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4 border-b border-warn-amber/20 pb-3">
              <h2 className="text-lg md:text-xl font-bold text-white flex items-center gap-2.5">
                {isSolution ? (
                  <>
                    <motion.span 
                      animate={{ scale: [1, 1.2, 1] }} 
                      transition={{ repeat: Infinity, duration: 2 }}
                    >
                      🤖
                    </motion.span> 
                    Gemini AI Co-Pilot Solution
                  </>
                ) : (
                  <>
                    <Zap className="w-5 h-5 text-warn-amber animate-pulse" /> 
                    AI Co-Pilot Resolution Prompt
                  </>
                )}
              </h2>
              <div className="flex items-center gap-2">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={copyToClipboard}
                  className="bg-navy-panel hover:bg-cyan-accent hover:text-navy-bg text-cyan-accent border border-cyan-accent/50 px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 uppercase font-mono"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-secure-green" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? '✓ Copied!' : 'Copy Prompt'}
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.05, boxShadow: '0 0 15px rgba(255,171,0,0.6)' }}
                  whileTap={{ scale: 0.95 }}
                  onClick={solveWithGemini}
                  disabled={aiLoading}
                  className="bg-warn-amber hover:bg-white text-navy-bg px-3.5 py-1.5 rounded-lg text-xs font-bold transition uppercase tracking-wider font-mono shadow-[0_0_10px_rgba(255,171,0,0.4)] flex items-center gap-1.5"
                >
                  {aiLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Running...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" /> {isSolution ? 'Re-run Fix' : 'Solve with Gemini'}
                    </>
                  )}
                </motion.button>
              </div>
            </div>

            <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-gray-200 max-h-96 overflow-y-auto pr-2 selection:bg-warn-amber/20">
              {aiFix}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Analysis Results with Staggered Animations */}
      <AnimatePresence>
        {analysis && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ type: "spring", stiffness: 200, damping: 20 }}
            className="bg-navy-panel rounded-2xl shadow-2xl p-6 md:p-8 border border-cyan-accent/30 space-y-6"
          >
            {/* Top Analysis Status Banner */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-cyan-accent/20">
              <div className="flex items-center gap-3">
                <motion.div 
                  initial={{ scale: 0.5, rotate: -20 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ type: "spring", stiffness: 300, damping: 15 }}
                  className={`p-3 rounded-xl border ${
                    analysis.status === 'Pass' 
                      ? 'bg-secure-green/20 border-secure-green text-secure-green shadow-[0_0_20px_rgba(0,230,118,0.3)]' 
                      : 'bg-critical-red/20 border-critical-red text-critical-red shadow-[0_0_20px_rgba(255,51,102,0.3)]'
                  }`}
                >
                  {analysis.status === 'Pass' ? (
                    <ShieldCheck className="w-7 h-7" />
                  ) : (
                    <ShieldAlert className="w-7 h-7 animate-pulse" />
                  )}
                </motion.div>

                <div>
                  <div className="text-xs font-bold text-gray-400 uppercase tracking-widest font-mono">
                    Security Verdict
                  </div>
                  <h2 className="text-2xl md:text-3xl font-black uppercase tracking-wider text-white flex items-center gap-3">
                    Status: 
                    <span className={analysis.status === 'Pass' ? 'text-secure-green' : 'text-critical-red drop-shadow-[0_0_10px_rgba(255,51,102,0.8)]'}>
                      {analysis.status}
                    </span>
                  </h2>
                </div>
              </div>

              {/* Finding Counters Pills */}
              <div className="flex items-center gap-3">
                <div className="bg-black/50 px-4 py-2 rounded-xl border border-gray-800 text-center">
                  <div className="text-[10px] uppercase font-bold text-gray-500">Total Findings</div>
                  <div className="text-xl font-black font-mono text-cyan-accent">
                    {analysis.findings.length}
                  </div>
                </div>

                <div className="bg-black/50 px-4 py-2 rounded-xl border border-critical-red/30 text-center">
                  <div className="text-[10px] uppercase font-bold text-critical-red">Critical</div>
                  <div className="text-xl font-black font-mono text-critical-red">
                    {criticalCount}
                  </div>
                </div>

                <div className="bg-black/50 px-4 py-2 rounded-xl border border-warn-amber/30 text-center">
                  <div className="text-[10px] uppercase font-bold text-warn-amber">Warnings</div>
                  <div className="text-xl font-black font-mono text-warn-amber">
                    {warningCount}
                  </div>
                </div>
              </div>
            </div>

            {/* Staggered Findings List */}
            <div className="space-y-4">
              {analysis.findings.map((finding, idx) => {
                const isCritical = finding.severity.toLowerCase().includes('crit');
                const isWarning = finding.severity.toLowerCase().includes('warn') || finding.severity.toLowerCase().includes('med');
                
                const borderColor = isCritical ? 'border-critical-red' : isWarning ? 'border-warn-amber' : 'border-cyan-accent';
                const bgColor = isCritical ? 'bg-critical-red/10' : isWarning ? 'bg-warn-amber/10' : 'bg-cyan-accent/10';
                const textColor = isCritical ? 'text-critical-red' : isWarning ? 'text-warn-amber' : 'text-cyan-accent';
                const glowShadow = isCritical ? 'shadow-[0_0_15px_rgba(255,51,102,0.15)]' : 'shadow-[0_0_15px_rgba(255,171,0,0.15)]';

                return (
                  <motion.div 
                    key={idx}
                    initial={{ opacity: 0, x: -25, scale: 0.98 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    transition={{ delay: idx * 0.07, type: "spring", stiffness: 220, damping: 20 }}
                    whileHover={{ scale: 1.01, x: 4 }}
                    className={`border-l-4 ${borderColor} ${bgColor} ${glowShadow} p-5 rounded-r-xl border-t border-r border-b border-white/5 transition-all relative group`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        {isCritical ? (
                          <AlertTriangle className="w-4 h-4 text-critical-red animate-pulse" />
                        ) : (
                          <ShieldAlert className="w-4 h-4 text-warn-amber" />
                        )}
                        <span className={`font-black font-mono text-xs uppercase tracking-widest ${textColor}`}>
                          [{finding.severity}]
                        </span>
                      </div>

                      <button
                        onClick={() => copyFindingText(finding.message, idx)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity text-xs font-mono text-gray-400 hover:text-white flex items-center gap-1 bg-black/40 px-2.5 py-1 rounded border border-gray-800"
                      >
                        {copiedFindingIdx === idx ? <Check className="w-3 h-3 text-secure-green" /> : <Copy className="w-3 h-3" />}
                        {copiedFindingIdx === idx ? 'Copied' : 'Copy'}
                      </button>
                    </div>

                    <div className="font-mono text-sm text-gray-100 break-words font-semibold bg-black/30 p-2.5 rounded-lg border border-white/5">
                      {finding.message}
                    </div>

                    {finding.recommendation && (
                      <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.1 + idx * 0.05 }}
                        className="mt-3.5 pt-3 border-t border-white/10"
                      >
                        <div className="flex items-start gap-2 text-xs font-mono text-gray-300 leading-relaxed">
                          <span className="text-cyan-accent font-bold uppercase tracking-wider shrink-0 flex items-center gap-1">
                            <Sparkles className="w-3.5 h-3.5" /> AI Suggestion:
                          </span>
                          <span className="text-gray-300">
                            {finding.recommendation}
                          </span>
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </motion.div>
  );
}

export default ManualAnalysis;
