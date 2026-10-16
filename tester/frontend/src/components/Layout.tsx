import { Outlet, Link, useLocation } from 'react-router-dom';
import { Shield, LayoutDashboard, GitBranch, Moon, Sun, LogOut, Bell, Compass, Terminal, FileCode, Globe, Server, CheckCircle2, ShieldCheck } from 'lucide-react';
import { useTheme } from '../context/useTheme';
import { useState, useEffect, useRef } from 'react';
import { apiClient } from '../config';

export default function Layout() {
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Admin Console', href: '/admin', icon: ShieldCheck },
    { name: 'System Assurance', href: '/assurance', icon: CheckCircle2 },
    { name: 'Project Hub', href: '/hub', icon: Compass },
    { name: 'Repositories', href: '/onboarding', icon: GitBranch },
    { name: 'Security Passport', href: '/passport', icon: Shield },
    { name: 'Live Terminal', href: '/scanner', icon: Terminal },
    { name: 'Log & Code Analyzer', href: '/analyzer', icon: FileCode },
    { name: 'Edge Diagnostics', href: '/diagnostics', icon: Globe },
    { name: 'Target Inventory', href: '/settings/targets', icon: Server },
  ];

  useEffect(() => {
    const fetchNotifications = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) return;
      try {
        const res = await apiClient.get(`/notifications`);
        setNotifications(res.data);
      } catch (e) {
        // Silently ignore if offline or session expired
      }
    };
    fetchNotifications();
    
    const interval = setInterval(fetchNotifications, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const markAsRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiClient.put(`/notifications/${id}/read`, {});
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (e) {
      console.error("Failed to mark as read", e);
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="flex h-screen bg-background-light dark:bg-background-dark">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-border-light dark:border-border-dark">
          <img src="/zylorun-logo.svg" alt="Zylorun Logo" className="w-8 h-8 rounded-lg mr-3 shadow-md bg-slate-900 border border-slate-700/60 p-0.5" />
          <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400 tracking-tight">
            Zylorun
          </span>
        </div>
        
        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-4 py-3 rounded-lg transition-colors ${
                  isActive 
                    ? 'bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 font-medium' 
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                }`}
              >
                <item.icon className={`w-5 h-5 mr-3 ${isActive ? 'text-brand-600 dark:text-brand-400' : 'text-slate-400'}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-border-light dark:border-border-dark space-y-2">
          <button 
            onClick={toggleTheme}
            className="flex items-center w-full px-4 py-2.5 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg transition-colors"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 mr-3" /> : <Moon className="w-4 h-4 mr-3" />}
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </button>
          <button 
            onClick={() => {
              localStorage.removeItem('access_token');
              window.location.href = '/';
            }}
            className="flex items-center w-full px-4 py-2.5 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg transition-colors">
            <LogOut className="w-4 h-4 mr-3" />
            Sign Out
          </button>
          
          <div className="pt-2">
            <a 
              href="https://www.vovalyx.in/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200/60 dark:border-slate-800 transition group"
            >
              <img src="/vovalyx-logo.png" alt="Vovalyx Logo" className="w-5 h-5 rounded object-contain shrink-0" />
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate group-hover:text-brand-500">Vovalyx</span>
                <span className="text-[10px] text-slate-400 truncate">Engineer your vision</span>
              </div>
            </a>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 border-b border-border-light dark:border-border-dark bg-surface-light/50 dark:bg-surface-dark/50 backdrop-blur-sm flex items-center justify-between px-8 z-10">
          <h1 className="text-xl font-semibold">
            {navigation.find(n => location.pathname.startsWith(n.href))?.name || 'Overview'}
          </h1>
          <div className="flex items-center space-x-4">
            
            <div className="relative" ref={notifRef}>
              <button 
                onClick={() => setShowNotifications(!showNotifications)}
                className="p-2 relative text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white dark:border-slate-900"></span>
                )}
              </button>

              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-slate-900 border border-border-light dark:border-border-dark rounded-xl shadow-xl overflow-hidden z-50">
                  <div className="p-4 border-b border-border-light dark:border-border-dark flex justify-between items-center">
                    <h3 className="font-semibold text-sm">Notifications</h3>
                    {unreadCount > 0 && (
                      <span className="text-xs bg-brand-100 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400 px-2 py-0.5 rounded-full font-medium">
                        {unreadCount} new
                      </span>
                    )}
                  </div>
                  <div className="max-h-[400px] overflow-y-auto">
                    {notifications.length === 0 ? (
                      <div className="p-4 text-center text-sm text-slate-500">No notifications</div>
                    ) : (
                      notifications.map((n, i) => (
                        <div key={i} className={`p-4 border-b border-border-light dark:border-border-dark last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer ${!n.is_read ? 'bg-slate-50/50 dark:bg-slate-800/20' : ''}`}>
                          <div className="flex justify-between items-start mb-1">
                            <span className="text-sm font-medium pr-4">{n.title || n.message}</span>
                            {!n.is_read && (
                              <button 
                                onClick={(e) => markAsRead(n.id, e)}
                                className="text-xs text-brand-500 hover:text-brand-600 whitespace-nowrap"
                              >
                                Mark read
                              </button>
                            )}
                          </div>
                          <p className="text-xs text-slate-500 mt-1">{n.created_at ? new Date(n.created_at).toLocaleString() : 'Date unavailable'}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

          </div>
        </header>
        <div className="flex-1 overflow-auto p-8">
          <Outlet />
        </div>

        {/* Permanent Vovalyx Footer */}
        <footer className="shrink-0 border-t border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md px-6 py-3 flex flex-wrap items-center justify-between gap-3 text-xs z-20">
          <div className="flex items-center gap-3">
            <a 
              href="https://www.vovalyx.in/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 group transition hover:opacity-90"
            >
              <img 
                src="/vovalyx-logo.png" 
                alt="Vovalyx Logo" 
                className="w-5 h-5 rounded object-contain"
              />
              <span className="font-bold text-slate-800 dark:text-slate-100 group-hover:text-brand-500 transition">
                Vovalyx
              </span>
            </a>
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <a 
              href="https://www.vovalyx.in/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-slate-600 dark:text-slate-300 hover:text-brand-500 dark:hover:text-brand-400 font-medium transition"
            >
              Vovalyx — Engineer your vision.
            </a>
          </div>
          <div className="text-slate-400 dark:text-slate-500 flex items-center gap-2">
            <span>Powered by Vovalyx</span>
            <span>&bull;</span>
            <a 
              href="https://www.vovalyx.in/" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="hover:underline text-brand-500"
            >
              www.vovalyx.in
            </a>
          </div>
        </footer>
      </main>
    </div>
  );
}
