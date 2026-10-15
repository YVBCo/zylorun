import React, { useState, useEffect, useRef } from 'react';
import { motion, useReducedMotion, AnimatePresence, useSpring, useMotionValue, useTransform } from 'framer-motion';
import { Shield, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import CanvasBackground from './CanvasBackground';

export default function Login({ setAuthToken }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  
  const [backendState, setBackendState] = useState('connecting'); // connecting, connected, error
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  
  const [attempts, setAttempts] = useState(0);
  const [lockoutTimer, setLockoutTimer] = useState(0);
  const [pendingLogin, setPendingLogin] = useState(false);
  
  const [isKonami, setIsKonami] = useState(false);
  const konamiIndex = useRef(0);
  
  const [effectsOn, setEffectsOn] = useState(() => localStorage.getItem('effects') !== 'off');
  
  const prefersReducedMotion = useReducedMotion();
  const navigate = useNavigate();
  
  // Intro Sequence State
  const [introStep, setIntroStep] = useState(0); 
  // 0: boot text, 1: show card, 2: typing title

  // Mouse for tilt & canvas
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const [mousePos, setMousePos] = useState({ x: -1000, y: -1000 });
  
  const smoothX = useSpring(mouseX, { damping: 20, stiffness: 100 });
  const smoothY = useSpring(mouseY, { damping: 20, stiffness: 100 });
  const rotateX = useTransform(smoothY, [0, typeof window !== 'undefined' ? window.innerHeight : 1000], [4, -4]);
  const rotateY = useTransform(smoothX, [0, typeof window !== 'undefined' ? window.innerWidth : 1000], [-4, 4]);

  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  const disableTilt = isMobile || prefersReducedMotion || !effectsOn;

  useEffect(() => {
    // Intro Sequence
    const played = sessionStorage.getItem('introPlayed');
    if (played) {
      setIntroStep(2);
    } else {
      const t1 = setTimeout(() => { setIntroStep(1); sessionStorage.setItem('introPlayed', 'true'); }, 1500);
      const t2 = setTimeout(() => setIntroStep(2), 2500);
      return () => { clearTimeout(t1); clearTimeout(t2); };
    }
  }, []);

  useEffect(() => {
    // Backend Check
    let mounted = true;
    const checkBackend = async () => {
      try {
        await fetch('https://software-testing-teq9.onrender.com/');
        if (mounted) setBackendState('connected');
      } catch (e) {
        if (mounted) setBackendState('error');
      }
    };
    checkBackend();

    // Konami
    const konami = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
    const handleKey = (e) => {
      if (e.key === konami[konamiIndex.current]) {
        konamiIndex.current++;
        if (konamiIndex.current === konami.length) {
          setIsKonami(prev => !prev);
          konamiIndex.current = 0;
        }
      } else {
        konamiIndex.current = 0;
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => {
      mounted = false;
      window.removeEventListener('keydown', handleKey);
    };
  }, []);

  useEffect(() => {
    if (pendingLogin && backendState === 'connected') {
      setPendingLogin(false);
      handleLogin(new Event('submit'));
    }
  }, [backendState, pendingLogin]);

  useEffect(() => {
    if (lockoutTimer > 0) {
      const timer = setTimeout(() => setLockoutTimer(lockoutTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [lockoutTimer]);

  const skipIntro = () => {
    setIntroStep(2);
    sessionStorage.setItem('introPlayed', 'true');
  };

  useEffect(() => {
    if (introStep === 0) {
      const skip = () => skipIntro();
      window.addEventListener('keydown', skip);
      return () => window.removeEventListener('keydown', skip);
    }
  }, [introStep]);

  const handleMouseMove = (e) => {
    if (disableTilt) return;
    mouseX.set(e.clientX);
    mouseY.set(e.clientY);
    setMousePos({ x: e.clientX, y: e.clientY });
  };

  const handleLogin = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (lockoutTimer > 0) return;
    
    if (backendState === 'connecting') {
      setErrorMsg('Backend is still waking up, please wait...');
      setPendingLogin(true);
      return;
    }

    setLoading(true);
    setErrorMsg('');

    try {
      const res = await fetch('https://software-testing-teq9.onrender.com/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username, password })
      });

      if (res.ok) {
        const data = await res.json();
        setSuccess(true);
        setTimeout(() => {
          localStorage.setItem('token', data.access_token);
          setAuthToken(data.access_token);
          navigate('/');
        }, 900);
      } else {
        const newAttempts = attempts + 1;
        setAttempts(newAttempts);
        setErrorMsg('Invalid credentials');
        setLoading(false);
        if (newAttempts >= 5) {
          setLockoutTimer(30);
          setAttempts(0);
        }
      }
    } catch (err) {
      setErrorMsg('Connection failed');
      setLoading(false);
    }
  };

  const toggleEffects = () => {
    const newVal = !effectsOn;
    setEffectsOn(newVal);
    localStorage.setItem('effects', newVal ? 'on' : 'off');
  };

  const primaryColor = isKonami ? 'rgba(34, 197, 94, 1)' : 'rgba(0, 229, 255, 1)';
  const bgClass = isKonami ? 'bg-green-500/20' : 'bg-cyan-500/20';
  const borderClass = isKonami ? 'border-green-400' : 'border-cyan-400';
  const textClass = isKonami ? 'text-green-400' : 'text-cyan-400';

  // Boot Text
  if (introStep === 0 && !prefersReducedMotion && effectsOn) {
    return (
      <div 
        className="min-h-screen bg-[#0b1220] flex items-center justify-center font-mono text-cyan-500 text-sm md:text-lg cursor-pointer"
        onClick={skipIntro}
      >
        <div className="space-y-2 relative animate-pulse">
          <div>{`> INITIALIZING SECURE CHANNEL...`}</div>
          <div>{`> LOADING ENCRYPTION MODULES... OK`}</div>
          <div>
            {`> VERIFYING BACKEND... `} 
            <span className={backendState === 'connected' ? 'text-green-500' : 'text-amber-500'}>
              {backendState === 'connected' ? 'OK' : 'WAKING UP'}
            </span>
          </div>
          <div className="absolute -bottom-10 left-0 text-xs text-gray-500">
            [Press any key or click to skip]
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`relative min-h-screen w-full bg-[#0b1220] flex flex-col items-center justify-center overflow-hidden font-sans selection:bg-cyan-500/30 perspective-[1000px]`}
      onMouseMove={handleMouseMove}
    >
      <CanvasBackground mousePos={mousePos} isMobile={isMobile} reducedMotion={prefersReducedMotion || !effectsOn} isKonami={isKonami} />

      {/* Top right HUD */}
      <div className="absolute top-4 right-4 z-50 flex flex-col items-end gap-1 font-mono text-xs text-gray-500">
        <div>SESSION: NEW</div>
        <button onClick={toggleEffects} className="mt-2 hover:text-white transition cursor-pointer">
          EFFECTS: {effectsOn ? 'ON' : 'OFF'}
        </button>
      </div>

      <AnimatePresence>
        {!success ? (
          <motion.div
            key="card"
            initial={{ opacity: 0, y: disableTilt ? 0 : 20 }}
            animate={errorMsg && !disableTilt ? ["visible", "shake"] : "visible"}
            exit={{ opacity: 0, scale: 0.96, transition: { duration: 0.3 } }}
            variants={{
              visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 100, damping: 20 } },
              shake: { x: [-12, 12, -9, 9, -4, 0], transition: { duration: 0.4 } }
            }}
            style={disableTilt ? {} : { rotateX, rotateY }}
            className={`relative z-10 w-full max-w-[420px] p-8 bg-[#0b1220]/90 backdrop-blur-md border border-gray-800 rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-hidden transition-colors duration-300 ${errorMsg ? 'border-red-500/50 shadow-red-500/20' : ''}`}
          >
            {/* Spotlight */}
            {!disableTilt && (
              <motion.div
                className="absolute inset-0 pointer-events-none opacity-30"
                style={{
                  background: `radial-gradient(300px circle at ${mousePos.x}px ${mousePos.y}px, ${primaryColor}, transparent 40%)`
                }}
              />
            )}
            
            {/* Corner Brackets */}
            <div className="absolute top-2 left-2 w-4 h-4 border-t-2 border-l-2 border-gray-600 animate-pulse" />
            <div className="absolute top-2 right-2 w-4 h-4 border-t-2 border-r-2 border-gray-600 animate-pulse" />
            <div className="absolute bottom-2 left-2 w-4 h-4 border-b-2 border-l-2 border-gray-600 animate-pulse" />
            <div className="absolute bottom-2 right-2 w-4 h-4 border-b-2 border-r-2 border-gray-600 animate-pulse" />

            {/* Glowing Border SVG */}
            {!disableTilt && !errorMsg && (
              <svg className="absolute inset-0 w-full h-full pointer-events-none rounded-2xl" style={{ stroke: primaryColor }}>
                <rect width="100%" height="100%" fill="none" strokeWidth="2" strokeDasharray="300 1500" className="animate-[dash_8s_linear_infinite]" rx="16" />
              </svg>
            )}

            {/* Header */}
            <div className="flex flex-col items-center mb-8 relative z-10">
              <div className="relative mb-4">
                <Shield className={`w-14 h-14 transition-colors duration-300 ${errorMsg ? 'text-red-500' : textClass}`} />
                {loading && (
                  <motion.div 
                    className={`absolute inset-0 rounded-full border-2 border-dashed ${borderClass}`}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                  />
                )}
                {!disableTilt && !errorMsg && !loading && (
                  <motion.div 
                    className={`absolute inset-0 rounded-full border ${borderClass}`}
                    animate={{ scale: [1, 1.8, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                  />
                )}
              </div>
              
              <h1 className={`text-3xl font-bold tracking-widest text-white ${errorMsg && !disableTilt ? 'animate-glitch' : ''}`}>
                SECRUNNER
              </h1>
              
              <div className="h-4 mt-1">
                {introStep >= 2 ? (
                  <motion.p 
                    initial={{ width: 0 }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 0.8, ease: "linear" }}
                    className={`text-xs tracking-[0.3em] uppercase font-mono overflow-hidden whitespace-nowrap border-r-2 ${borderClass} animate-pulse ${textClass}`}
                  >
                    SECURITY PLATFORM
                  </motion.p>
                ) : null}
              </div>
            </div>

            <form onSubmit={handleLogin} className="space-y-6 relative z-10">
              {/* Inputs */}
              <div className="relative group">
                <label className={`absolute -top-2.5 left-3 bg-[#0b1220] px-1 text-[10px] font-mono text-gray-500 group-focus-within:${textClass} transition-colors z-10`}>
                  USERNAME
                </label>
                <input
                  type="text"
                  required
                  autoComplete="off"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className={`w-full bg-white/5 border border-gray-700 rounded px-4 py-3 text-white outline-none focus:${borderClass} transition-all focus:shadow-[0_0_15px_${primaryColor.replace('1)', '0.2)')}] autofill-override`}
                />
                <div className={`absolute bottom-0 left-0 h-[2px] bg-gradient-to-r from-transparent via-${isKonami?'green':'cyan'}-400 to-transparent w-0 group-focus-within:w-full transition-all duration-500`} />
              </div>

              <div className="relative group">
                <label className={`absolute -top-2.5 left-3 bg-[#0b1220] px-1 text-[10px] font-mono text-gray-500 group-focus-within:${textClass} transition-colors z-10`}>
                  PASSWORD
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    autoComplete="off"
                    value={password}
                    onKeyUp={(e) => setCapsLock(e.getModifierState('CapsLock'))}
                    onChange={(e) => setPassword(e.target.value)}
                    className={`w-full bg-white/5 border border-gray-700 rounded px-4 py-3 text-white outline-none focus:${borderClass} transition-all focus:shadow-[0_0_15px_${primaryColor.replace('1)', '0.2)')}] pr-12 autofill-override`}
                  />
                  <div className={`absolute bottom-0 left-0 h-[2px] bg-gradient-to-r from-transparent via-${isKonami?'green':'cyan'}-400 to-transparent w-0 group-focus-within:w-full transition-all duration-500`} />
                  
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                    {capsLock && (
                      <AlertTriangle className="w-4 h-4 text-amber-500 animate-pulse" title="Caps Lock is ON" />
                    )}
                    <button 
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className={`text-gray-500 hover:${textClass} transition-colors`}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Error */}
              <AnimatePresence>
                {errorMsg && (
                  <motion.div 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="text-red-400 text-xs font-mono bg-red-500/10 border border-red-500/20 rounded px-3 py-2 flex items-center justify-between overflow-hidden"
                    aria-live="assertive"
                  >
                    <div className="flex items-center gap-2">
                      <AlertTriangle size={14} /> {errorMsg}
                    </div>
                    {attempts > 0 && <span className="opacity-70">Attempt {attempts}/5</span>}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Button */}
              <motion.button
                whileHover={!disableTilt && !loading && lockoutTimer === 0 ? { scale: 1.02, textShadow: "0 0 8px rgb(255,255,255)" } : {}}
                whileTap={!disableTilt && !loading && lockoutTimer === 0 ? { scale: 0.98 } : {}}
                disabled={loading || lockoutTimer > 0}
                className={`relative w-full ${bgClass} ${borderClass} border ${textClass} font-bold tracking-widest py-3 rounded mt-6 overflow-hidden transition-colors ${lockoutTimer === 0 ? `hover:${bgClass.replace('/20', '/40')} hover:text-white` : 'opacity-50 cursor-not-allowed'} group`}
              >
                {lockoutTimer > 0 ? (
                  `LOCKED (${lockoutTimer}s)`
                ) : loading ? (
                  <div className="flex items-center justify-center gap-2 relative z-10">
                    <span className="animate-pulse">AUTHENTICATING...</span>
                  </div>
                ) : (
                  <span className="relative z-10">AUTHENTICATE</span>
                )}
                {loading && !disableTilt && (
                  <motion.div 
                    initial={{ x: "-100%" }}
                    animate={{ x: "100%" }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    className={`absolute inset-0 ${bgClass.replace('/20', '/40')} z-0 skew-x-12`}
                  />
                )}
              </motion.button>
            </form>
            
            {loading && (
              <div className="mt-4 text-center font-mono text-[10px] text-gray-500 animate-pulse">
                Verifying identity... Checking credentials...
              </div>
            )}
          </motion.div>
        ) : (
          <motion.div 
            key="success"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center z-10 relative"
          >
            {/* Shockwave */}
            {!disableTilt && (
              <motion.div
                initial={{ scale: 0.5, opacity: 1 }}
                animate={{ scale: 3, opacity: 0 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="absolute inset-0 rounded-full border-4 border-green-500"
              />
            )}
            
            <Shield className="w-24 h-24 text-green-500 mb-6 drop-shadow-[0_0_20px_rgba(34,197,94,0.8)] relative z-10" />
            <motion.h2 
              initial={{ letterSpacing: "2px" }}
              animate={{ letterSpacing: "8px" }}
              className="text-3xl font-bold text-green-400 font-mono drop-shadow-[0_0_10px_rgba(34,197,94,0.8)]"
            >
              ACCESS GRANTED
            </motion.h2>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer Pill & Text */}
      <div className="absolute bottom-8 flex flex-col items-center gap-2 w-full px-4">
        <div className="bg-black/40 backdrop-blur border border-gray-800 rounded-full px-4 py-2 flex items-center gap-3 text-xs font-mono shadow-xl">
          <div className={`w-2 h-2 rounded-full ${backendState === 'connected' ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : backendState === 'error' ? 'bg-red-500' : 'bg-amber-500 animate-pulse'}`} />
          <span className={backendState === 'connected' ? 'text-green-400' : backendState === 'error' ? 'text-red-400' : 'text-amber-400'}>
            {backendState === 'connected' ? 'Backend connected' : backendState === 'error' ? 'Backend unreachable' : 'Waking secure backend... ~30s'}
          </span>
          {backendState === 'connecting' && (
            <div className="w-16 h-1 bg-gray-800 rounded overflow-hidden">
              <motion.div 
                className="h-full bg-amber-500"
                initial={{ x: "-100%" }}
                animate={{ x: "100%" }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
              />
            </div>
          )}
        </div>
        <p className="text-gray-600 text-[10px] uppercase tracking-widest font-mono">
          Authorized use only. All access is logged.
        </p>
      </div>
    </div>
  );
}
