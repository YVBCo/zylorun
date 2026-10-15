import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, Navigate, Link } from 'react-router-dom';
import { Terminal, Shield, PlayCircle, FileText, Settings as SettingsIcon, LogOut, PlusCircle, Activity, Menu, X } from 'lucide-react';
import { motion } from 'framer-motion';
import ManualAnalysis from './ManualAnalysis';
import Login from './Login';
import Settings from './Settings';
import CommandPrompt from './CommandPrompt';
import CommandRun from './CommandRun';

// Helper for Animated Numbers
function AnimatedNumber({ value }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = 0;
    const duration = 1000;
    const interval = 20;
    const step = (value / duration) * interval;
    const timer = setInterval(() => {
      start += step;
      if (start >= value) {
        setDisplay(value);
        clearInterval(timer);
      } else {
        setDisplay(Math.floor(start));
      }
    }, interval);
    return () => clearInterval(timer);
  }, [value]);
  return <span>{display}</span>;
}

function Dashboard() {
  const navigate = useNavigate();
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 md:p-8 h-full overflow-y-auto"
    >
      <div className="flex items-center gap-3 mb-8">
        <Activity className="w-8 h-8 text-cyan-accent" />
        <h1 className="text-2xl md:text-3xl font-bold text-white tracking-wide">SecRunner HQ</h1>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {[
          { title: "Total Scans", value: 248, color: "text-cyan-accent", trend: "+12%" },
          { title: "Targets", value: 12, color: "text-secure-green", trend: "Active" },
          { title: "Critical Findings", value: 7, color: "text-critical-red", trend: "+2" },
          { title: "Active Tools", value: 5, color: "text-warn-amber", trend: "Ready" }
        ].map((stat, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1 }}
            className="bg-navy-panel p-6 rounded-xl border border-cyan-accent/20 flex flex-col justify-between"
          >
            <div className="text-gray-400 text-sm font-semibold uppercase">{stat.title}</div>
            <div className="flex items-end justify-between mt-4">
              <div className={`text-4xl font-bold font-mono ${stat.color}`}>
                <AnimatedNumber value={stat.value} />
              </div>
              <div className="text-xs text-gray-500 font-mono">{stat.trend}</div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div 
          whileHover={{ scale: 1.02 }}
          onClick={() => navigate('/run')}
          className="bg-navy-panel p-8 rounded-xl shadow-lg border border-cyan-accent/20 cursor-pointer hover:border-cyan-accent/50 transition group"
        >
          <PlayCircle className="w-12 h-12 text-cyan-accent mb-4 group-hover:scale-110 transition-transform" />
          <h2 className="text-xl font-bold text-white mb-2">Live Terminal</h2>
          <p className="text-gray-400 text-sm">Execute OS-level security scans in real-time securely.</p>
        </motion.div>

        <motion.div 
          whileHover={{ scale: 1.02 }}
          onClick={() => navigate('/analyze')}
          className="bg-navy-panel p-8 rounded-xl shadow-lg border border-warn-amber/20 cursor-pointer hover:border-warn-amber/50 transition group"
        >
          <FileText className="w-12 h-12 text-warn-amber mb-4 group-hover:scale-110 transition-transform" />
          <h2 className="text-xl font-bold text-white mb-2">Log Analyzer</h2>
          <p className="text-gray-400 text-sm">Upload massive ZIP files for instant vulnerability scanning.</p>
        </motion.div>

        <motion.div 
          whileHover={{ scale: 1.02 }}
          onClick={() => navigate('/manage-commands')}
          className="bg-navy-panel p-8 rounded-xl shadow-lg border border-secure-green/20 cursor-pointer hover:border-secure-green/50 transition group"
        >
          <PlusCircle className="w-12 h-12 text-secure-green mb-4 group-hover:scale-110 transition-transform" />
          <h2 className="text-xl font-bold text-white mb-2">Grid Config</h2>
          <p className="text-gray-400 text-sm">Manage tools and target IP addresses visually.</p>
        </motion.div>
      </div>
    </motion.div>
  );
}

function RunCommand({ token }) {
  const [output, setOutput] = useState([]);
  const [status, setStatus] = useState("Idle");
  const [commands, setCommands] = useState([]);
  const [targets, setTargets] = useState([]);
  const [selectedCmd, setSelectedCmd] = useState('');
  const [selectedTarget, setSelectedTarget] = useState('');
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    fetch('https://software-testing-teq9.onrender.com/commands/', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => {
      setCommands(data);
      if (data.length > 0) setSelectedCmd(data[0].id);
    });

    fetch('https://software-testing-teq9.onrender.com/targets/', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => {
      setTargets(data);
      if (data.length > 0) setSelectedTarget(data[0].id);
    });
  }, [token]);

  // Timer logic
  useEffect(() => {
    let timer;
    if (status === "Running") {
      timer = setInterval(() => setElapsed(prev => prev + 1), 1000);
    }
    return () => clearInterval(timer);
  }, [status]);

  const startRun = () => {
    if (!selectedCmd || !selectedTarget) return;
    setStatus("Running");
    setOutput([]);
    setElapsed(0);
    
    const ws = new WebSocket(`wss://software-testing-teq9.onrender.com/runs/ws/${selectedCmd}/${selectedTarget}?token=${token}`);
    
    ws.onopen = () => {
      const cmd = commands.find(c => c.id == selectedCmd);
      const args = cmd ? JSON.parse(cmd.allowed_args) : [];
      ws.send(JSON.stringify({ args: args }));
    };
    
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.stream) {
        setOutput(prev => [...prev, msg.data]);
      } else if (msg.status) {
        setStatus(msg.status);
      } else if (msg.error) {
        setOutput(prev => [...prev, `[ERROR] ${msg.error}`]);
        setStatus("Failed");
      }
    };
    
    ws.onclose = () => {
      if (status === "Running") setStatus("Done");
    };
  };

  const getStatusColor = () => {
    switch (status.toLowerCase()) {
      case 'running': return 'text-warn-amber';
      case 'done': case 'completed': return 'text-secure-green';
      case 'failed': case 'error': return 'text-critical-red';
      default: return 'text-gray-400';
    }
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4 md:p-8 h-full flex flex-col">
      <h1 className="text-2xl md:text-3xl font-bold mb-6 text-white tracking-wide">Live Runner Ops</h1>
      
      {/* Control Panel */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center gap-4 mb-6 bg-navy-panel p-4 rounded-xl border border-cyan-accent/20">
        <select 
          className="bg-black/40 border border-gray-700 text-cyan-accent p-3 rounded font-mono outline-none focus:border-cyan-accent"
          value={selectedCmd}
          onChange={(e) => setSelectedCmd(e.target.value)}
        >
          {commands.map(c => <option key={c.id} value={c.id}>Tool: {c.name}</option>)}
        </select>

        <select 
          className="bg-black/40 border border-gray-700 text-cyan-accent p-3 rounded font-mono outline-none focus:border-cyan-accent"
          value={selectedTarget}
          onChange={(e) => setSelectedTarget(e.target.value)}
        >
          {targets.map(t => <option key={t.id} value={t.id}>Target: {t.name} ({t.host})</option>)}
        </select>
        
        <button 
          onClick={startRun}
          disabled={status === "Running" || !selectedCmd || !selectedTarget}
          className="px-8 py-3 bg-cyan-accent text-navy-bg font-bold tracking-widest uppercase rounded shadow-[0_0_15px_rgba(0,229,255,0.4)] hover:shadow-[0_0_25px_rgba(255,255,255,0.8)] hover:bg-white transition disabled:opacity-50 disabled:shadow-none"
        >
          Run Scan
        </button>
        
        <div className="md:ml-auto flex items-center justify-between gap-6 font-mono bg-black/40 py-2 px-4 rounded border border-gray-800">
          <div className="flex items-center gap-2">
            <span className="text-gray-500 uppercase text-xs">Status</span>
            <span className={`font-bold uppercase ${getStatusColor()} ${status === 'Running' ? 'animate-pulse' : ''}`}>{status}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-500 uppercase text-xs">Time</span>
            <span className="text-white font-bold">{formatTime(elapsed)}</span>
          </div>
        </div>
      </div>
      
      {/* Terminal Window */}
      <div className="flex-1 bg-black rounded-xl p-4 overflow-y-auto font-mono text-sm shadow-[inset_0_0_20px_rgba(0,0,0,1)] border border-gray-800 relative">
        {output.length === 0 && status === "Idle" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-700">
            <Terminal className="w-16 h-16 mb-4 opacity-20" />
            <p>System Ready. Awaiting Command...</p>
          </div>
        )}
        {output.map((line, i) => {
          let color = "text-gray-300";
          if (line.includes('[ERROR]') || line.toLowerCase().includes('fail') || line.toLowerCase().includes('critical')) color = "text-critical-red";
          else if (line.includes('[WARNING]') || line.toLowerCase().includes('warn')) color = "text-warn-amber";
          else if (line.includes('[INFO]') || line.toLowerCase().includes('success') || line.toLowerCase().includes('open')) color = "text-secure-green";
          
          return (
            <motion.div initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} key={i} className={`mb-1 ${color}`}>
              <span className="text-gray-700 mr-3">{(i+1).toString().padStart(4, '0')}</span> 
              {line}
            </motion.div>
          );
        })}
        {status === "Running" && <div className="text-cyan-accent animate-pulse mt-2 ml-10">_</div>}
      </div>
    </motion.div>
  );
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    fetch('https://software-testing-teq9.onrender.com/').catch(() => {});
  }, []);

  if (!token) {
    return <Login setAuthToken={setToken} />;
  }

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  return (
    <div className="h-screen w-screen bg-navy-bg flex flex-col md:flex-row overflow-hidden font-sans text-gray-200">
      
      {/* Mobile Header */}
      <div className="md:hidden bg-navy-panel border-b border-cyan-accent/20 p-4 flex items-center justify-between z-30">
        <div className="flex items-center gap-2 text-xl font-bold text-white tracking-widest">
          <Shield className="text-cyan-accent w-6 h-6" /> SECRUNNER
        </div>
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="text-cyan-accent">
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      <aside className={`w-64 bg-navy-panel border-r border-cyan-accent/20 p-6 flex flex-col shadow-2xl z-20 absolute md:relative h-full transition-transform transform ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}>
        <div className="hidden md:flex items-center gap-3 text-2xl font-bold text-white mb-10 tracking-widest">
          <Shield className="text-cyan-accent w-8 h-8 drop-shadow-[0_0_8px_rgba(0,229,255,0.8)]" /> 
          SECRUNNER
        </div>
        <nav className="space-y-4 flex-1">
          <Link onClick={() => setMobileMenuOpen(false)} to="/" className="flex items-center gap-3 p-3 rounded-lg hover:bg-cyan-accent/10 hover:text-cyan-accent transition font-semibold text-gray-400">
             <Activity className="w-5 h-5"/> Dashboard
          </Link>
          <div className="space-y-1">
            <Link onClick={() => setMobileMenuOpen(false)} to="/run" className="flex items-center gap-3 p-3 rounded-lg hover:bg-cyan-accent/10 hover:text-cyan-accent transition font-semibold text-gray-400">
               <Terminal className="w-5 h-5"/> Terminal Ops
            </Link>
            <div className="pl-4 border-l border-cyan-accent/20 ml-6 flex flex-col gap-2 pt-1">
              <Link onClick={() => setMobileMenuOpen(false)} to="/command-run" className="flex items-center gap-3 p-2 rounded-lg hover:bg-cyan-accent/10 hover:text-cyan-accent transition font-semibold text-gray-400 text-sm">
                <Terminal className="w-4 h-4"/> Command Run
              </Link>
            </div>
          </div>
          <div className="space-y-1">
            <Link onClick={() => setMobileMenuOpen(false)} to="/analyze" className="flex items-center gap-3 p-3 rounded-lg hover:bg-cyan-accent/10 hover:text-cyan-accent transition font-semibold text-gray-400">
               <FileText className="w-5 h-5"/> Analyzer
            </Link>
            <div className="pl-4 border-l border-cyan-accent/20 ml-6 flex flex-col gap-2 pt-1">
              <Link onClick={() => setMobileMenuOpen(false)} to="/command-prompt" className="flex items-center gap-3 p-2 rounded-lg hover:bg-cyan-accent/10 hover:text-cyan-accent transition font-semibold text-gray-400 text-sm">
                <Terminal className="w-4 h-4"/> Command Prompt
              </Link>
            </div>
          </div>
          <Link onClick={() => setMobileMenuOpen(false)} to="/manage-commands" className="flex items-center gap-3 p-3 rounded-lg hover:bg-cyan-accent/10 hover:text-cyan-accent transition font-semibold text-gray-400">
             <SettingsIcon className="w-5 h-5"/> Settings
          </Link>
        </nav>
        <button onClick={handleLogout} className="flex items-center justify-center gap-2 text-critical-red p-3 hover:bg-critical-red/10 rounded-lg transition font-bold text-sm uppercase tracking-wider border border-critical-red/20 mt-auto">
          <LogOut className="w-4 h-4" /> Disconnect
        </button>
      </aside>
      <main className="flex-1 relative z-10 overflow-hidden bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-navy-panel via-navy-bg to-navy-bg">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/run" element={<RunCommand token={token}/>} />
          <Route path="/analyze" element={<ManualAnalysis />} />
          <Route path="/command-run" element={<CommandRun token={token}/>} />
          <Route path="/command-prompt" element={<CommandPrompt token={token}/>} />
          <Route path="/manage-commands" element={<Settings token={token}/>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  )
}
