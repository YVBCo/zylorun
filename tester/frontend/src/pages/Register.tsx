import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiClient } from '../config';

export default function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.post(`/auth/register`, {
        username: name,
        email: email,
        password: password
      });
      
      const formData = new URLSearchParams();
      formData.append('username', name);
      formData.append('password', password);
      
      const loginRes = await apiClient.post(`/auth/login`, formData);
      localStorage.setItem('access_token', loginRes.data.access_token);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden bg-background-light dark:bg-background-dark">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-500/10 blur-[100px] rounded-full pointer-events-none" />
      
      <div className="w-full max-w-md p-8 rounded-2xl bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark shadow-xl shadow-black/5 dark:shadow-black/20 z-10">
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4 bg-slate-900 border border-slate-700/60 shadow-xl shadow-cyan-950/20">
            <img src="/zylorun-logo.svg" alt="Zylorun Logo" className="w-full h-full object-contain p-2" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight mb-1 text-white">Create your Zylorun Account</h2>
          <p className="text-sm text-slate-400">Autonomous Software Risk & Assurance Platform</p>
        </div>

        {error && <div className="mb-4 text-red-500 text-sm text-center">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5 text-slate-700 dark:text-slate-300">Name</label>
            <input 
              type="text" 
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:outline-none focus:ring-2 focus:ring-brand-500/50 transition-shadow"
              placeholder="Jane Doe"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5 text-slate-700 dark:text-slate-300">Email</label>
            <input 
              type="email" 
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:outline-none focus:ring-2 focus:ring-brand-500/50 transition-shadow"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5 text-slate-700 dark:text-slate-300">Password</label>
            <input 
              type="password" 
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:outline-none focus:ring-2 focus:ring-brand-500/50 transition-shadow"
              placeholder="••••••••"
            />
          </div>
          <button type="submit" className="w-full py-2.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white font-medium transition-colors mt-2 shadow-lg shadow-brand-500/25">
            Create Account
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-slate-500">
          Already have an account?{' '}
          <Link to="/login" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">
            Sign in
          </Link>
        </div>

        <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800/80 text-center">
          <a
            href="https://www.vovalyx.in/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-xs text-slate-500 hover:text-brand-500 transition"
          >
            <img src="/vovalyx-logo.png" alt="Vovalyx" className="w-4 h-4 rounded object-contain" />
            <span className="font-semibold text-slate-700 dark:text-slate-300">Vovalyx</span>
            <span>— Engineer your vision.</span>
          </a>
        </div>
      </div>
    </div>
  );
}
