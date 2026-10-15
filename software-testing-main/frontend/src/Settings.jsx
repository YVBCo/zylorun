import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export default function Settings({ token }) {
  const [commands, setCommands] = useState([]);
  const [targets, setTargets] = useState([]);
  
  const [newCmd, setNewCmd] = useState({ name: '', executable: '', allowed_args: '[]', timeout_seconds: 30, regex_rules: '{}' });
  const [newTarget, setNewTarget] = useState({ name: '', host: '', description: '' });

  const fetchSettings = () => {
    fetch('https://software-testing-teq9.onrender.com/commands/', { headers: { 'Authorization': 'Bearer ' + token } })
      .then(r => r.json()).then(setCommands);
    fetch('https://software-testing-teq9.onrender.com/targets/', { headers: { 'Authorization': 'Bearer ' + token } })
      .then(r => r.json()).then(setTargets);
  };

  useEffect(() => { fetchSettings(); }, [token]);

  const addCommand = async (e) => {
    if (e) e.preventDefault();
    try {
      const payload = {
        ...newCmd,
        allowed_args: JSON.parse(newCmd.allowed_args),
        regex_rules: JSON.parse(newCmd.regex_rules),
        timeout_seconds: parseInt(newCmd.timeout_seconds) || 30
      };
      
      const res = await fetch('https://software-testing-teq9.onrender.com/commands/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setNewCmd({ name: '', executable: '', allowed_args: '[]', timeout_seconds: 30, regex_rules: '{}' });
        fetchSettings();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.detail || "Failed to add command. Ensure the name is unique.");
      }
    } catch(err) {
      alert("Invalid JSON format in Args or Rules!");
    }
  };

  const addTarget = async (e) => {
    if (e) e.preventDefault();
    const res = await fetch('https://software-testing-teq9.onrender.com/targets/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify(newTarget)
    });
    if (res.ok) {
      setNewTarget({ name: '', host: '', description: '' });
      fetchSettings();
    } else {
      alert("Failed to add target.");
    }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4 md:p-8 h-full flex flex-col">
      <h1 className="text-2xl md:text-3xl font-bold text-white tracking-wide mb-8">Grid Configuration</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 flex-1 overflow-y-auto pb-10">
        
        {/* Commands Config */}
        <div className="bg-navy-panel p-6 rounded-xl border border-secure-green/30 shadow-[inset_0_0_20px_rgba(0,0,0,0.8)] flex flex-col">
          <h2 className="text-xl font-bold text-white mb-6 border-b border-gray-800 pb-2 uppercase tracking-widest">Security Protocols</h2>
          
          <div className="space-y-4 mb-8 flex-1 overflow-auto max-h-64">
            {commands.map(c => (
              <motion.div whileHover={{ x: 5 }} key={c.id} className="bg-black/60 p-4 border-l-2 border-secure-green rounded-r shadow mb-2">
                <div className="font-mono text-secure-green font-bold">{c.name} <span className="text-gray-500 text-xs">({c.executable})</span></div>
                <div className="text-xs text-gray-500 font-mono mt-1 break-words">{c.allowed_args}</div>
              </motion.div>
            ))}
          </div>
          
          <form onSubmit={addCommand} className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-2">
              <input 
                required
                className="bg-black/50 border border-gray-800 text-white p-3 rounded font-mono text-sm outline-none focus:border-secure-green transition" 
                placeholder="Tool Name (e.g. Ping)" 
                value={newCmd.name} 
                onChange={e => setNewCmd({...newCmd, name: e.target.value})} 
              />
              <input 
                required
                className="bg-black/50 border border-gray-800 text-white p-3 rounded font-mono text-sm outline-none focus:border-secure-green transition" 
                placeholder="Exec (e.g. ping)" 
                value={newCmd.executable} 
                onChange={e => setNewCmd({...newCmd, executable: e.target.value})} 
              />
            </div>
            <input 
              required
              className="bg-black/50 border border-gray-800 text-white p-3 rounded font-mono text-sm outline-none focus:border-secure-green transition" 
              placeholder='Args JSON (e.g. ["-c", "4"])' 
              value={newCmd.allowed_args} 
              onChange={e => setNewCmd({...newCmd, allowed_args: e.target.value})} 
            />
            <button 
              type="submit"
              className="bg-secure-green text-navy-bg font-bold p-3 rounded uppercase tracking-widest hover:bg-white transition mt-2 shadow-[0_0_15px_rgba(0,255,153,0.3)] hover:shadow-[0_0_20px_rgba(255,255,255,0.8)]"
            >
              Add Protocol
            </button>
          </form>
        </div>

        {/* Targets Config */}
        <div className="bg-navy-panel p-6 rounded-xl border border-cyan-accent/30 shadow-[inset_0_0_20px_rgba(0,0,0,0.8)] flex flex-col">
          <h2 className="text-xl font-bold text-white mb-6 border-b border-gray-800 pb-2 uppercase tracking-widest">Target Vectors</h2>
          
          <div className="space-y-4 mb-8 flex-1 overflow-auto max-h-64">
            {targets.map(t => (
              <motion.div whileHover={{ x: 5 }} key={t.id} className="bg-black/60 p-4 border-l-2 border-cyan-accent rounded-r shadow mb-2">
                <div className="font-mono text-cyan-accent font-bold">{t.name}</div>
                <div className="text-xs text-gray-500 font-mono mt-1">{t.host}</div>
                <div className="text-xs text-gray-600 mt-1">{t.description}</div>
              </motion.div>
            ))}
          </div>
          
          <form onSubmit={addTarget} className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-2">
              <input 
                required
                className="bg-black/50 border border-gray-800 text-white p-3 rounded font-mono text-sm outline-none focus:border-cyan-accent transition" 
                placeholder="Target (e.g. DB)" 
                value={newTarget.name} 
                onChange={e => setNewTarget({...newTarget, name: e.target.value})} 
              />
              <input 
                required
                className="bg-black/50 border border-gray-800 text-white p-3 rounded font-mono text-sm outline-none focus:border-cyan-accent transition" 
                placeholder="IP / Domain" 
                value={newTarget.host} 
                onChange={e => setNewTarget({...newTarget, host: e.target.value})} 
              />
            </div>
            <input 
              required
              className="bg-black/50 border border-gray-800 text-white p-3 rounded font-mono text-sm outline-none focus:border-cyan-accent transition" 
              placeholder="Description (e.g. Staging DB)" 
              value={newTarget.description} 
              onChange={e => setNewTarget({...newTarget, description: e.target.value})} 
            />
            <button 
              type="submit"
              className="bg-cyan-accent text-navy-bg font-bold p-3 rounded uppercase tracking-widest hover:bg-white transition mt-2 shadow-[0_0_15px_rgba(0,229,255,0.3)] hover:shadow-[0_0_20px_rgba(255,255,255,0.8)]"
            >
              Add Target
            </button>
          </form>
        </div>

      </div>
    </motion.div>
  );
}
