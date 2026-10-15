import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Landing() {
  const navigate = useNavigate();
  const [bootOut, setBootOut] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState(0);
  const [activeLayer, setActiveLayer] = useState(0);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authSuccess, setAuthSuccess] = useState('');

  // Canvas refs
  const bgCanvasRef = useRef<HTMLCanvasElement>(null);
  const globeCanvasRef = useRef<HTMLCanvasElement>(null);
  const authCanvasRef = useRef<HTMLCanvasElement>(null);

  // DOM refs
  const heroRef = useRef<HTMLDivElement>(null);
  const xrayRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const h1Ref = useRef<HTMLHeadingElement>(null);
  const heroTypingRef = useRef<HTMLDivElement>(null);
  const railFillRef = useRef<HTMLElement>(null);
  const railBulbRef = useRef<HTMLElement>(null);
  const pipeLineRef = useRef<HTMLElement>(null);
  const terminalOutRef = useRef<HTMLPreElement>(null);
  const terminalProgressRef = useRef<HTMLElement>(null);
  const scanSectionRef = useRef<HTMLElement>(null);
  const scanBeamRef = useRef<HTMLDivElement>(null);
  const scanRingRef = useRef<SVGCircleElement>(null);
  const scanCurFileRef = useRef<HTMLDivElement>(null);
  const scanCurStepRef = useRef<HTMLDivElement>(null);
  const scanWhyRef = useRef<HTMLDivElement>(null);
  const scanVerdictRef = useRef<HTMLDivElement>(null);
  const meterB1Ref = useRef<HTMLElement>(null);
  const meterB2Ref = useRef<HTMLElement>(null);
  const meterB3Ref = useRef<HTMLElement>(null);

  // Audio / pulse helper
  const authPulseRef = useRef<(() => void) | null>(null);

  const features = [
    { title: 'Penetration Testing', x: 50, y: 8, desc: 'Learn how attackers find weaknesses so you can find them first, using authorized lab targets only.' },
    { title: 'Network Security', x: 88, y: 28, desc: 'Explore firewalls, scanning and traffic analysis in a contained environment.' },
    { title: 'Web App Security', x: 88, y: 72, desc: 'Study injection, authentication and access-control flaws in practice apps.' },
    { title: 'Vulnerability Assessment', x: 50, y: 92, desc: 'Practice prioritizing findings and writing clear, understandable reports.' },
    { title: 'SIEM and Monitoring', x: 12, y: 72, desc: 'Read logs, spot patterns and understand how detection works.' },
    { title: 'Incident Response', x: 12, y: 28, desc: 'Rehearse the steps from first alert to recovery.' },
  ];

  const terminalSteps = [
    { text: 'Initializing lab environment', status: 0 },
    { text: 'Environment ready, sandboxed and offline', status: 1 },
    { text: 'Target lab example test', status: 0 },
    { text: 'Starting sample test suite', status: 0 },
    { text: 'Header checks ok', status: 1 },
    { text: 'Port exposure ok', status: 1 },
    { text: 'Cookie flags, one sample warning', status: 2 },
    { text: 'Input handling ok', status: 1 },
    { text: 'Suite complete. Three passed, one sample warning.', status: 1 },
    { text: 'This was scripted output. No real system was scanned.', status: 0 },
  ];

  const scanFiles = [
    { name: 'Login form', status: 'clean', note: 'This form takes a password and handles it safely, so it looks clean.' },
    { name: 'Database settings', status: 'issue', note: 'A password was left in plain text in this settings file. This is a sample issue.' },
    { name: 'Payment handler', status: 'review', note: 'It handles money and a few checks are missing, so a person should review it.' },
    { name: 'File upload', status: 'issue', note: 'Users can send any file type here. This is a sample issue.' },
    { name: 'Session manager', status: 'clean', note: 'Sign in sessions expire properly, so it looks clean.' },
    { name: 'Dependency list', status: 'review', note: 'One outside package looks old, so it needs review.' },
    { name: 'Search page', status: 'clean', note: 'Typed text is cleaned before use, so it looks clean.' },
    { name: 'Admin panel', status: 'review', note: 'Access rules need a second look, so it needs review.' }
  ];

  const scanStages = ['Reading file', 'Checking inputs', 'Looking for secrets', 'Rating risk'];
  const scanStageDescriptions = [
    'Opening the file and working out what it does.',
    'Seeing how it handles what users type or send.',
    'Searching for passwords or keys left in plain sight.',
    'Assessing residual risk profile against security baselines.'
  ];

  // 1. Decrypt text effect helper
  const decryptText = (element: HTMLElement | null, text: string) => {
    if (!element) return;
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
    let frame = 0;
    const totalFrames = 26;
    const interval = setInterval(() => {
      frame++;
      element.textContent = text
        .split('')
        .map((c, i) => (c === ' ' || i < (frame * text.length) / totalFrames ? c : chars[Math.floor(Math.random() * chars.length)]))
        .join('');
      if (frame >= totalFrames) {
        element.textContent = text;
        clearInterval(interval);
      }
    }, 25);
  };

  // 2. Terminal runner simulation
  const runTerminalDemo = (fast = false) => {
    const out = terminalOutRef.current;
    const pb = terminalProgressRef.current;
    if (!out || !pb) return;
    out.innerHTML = '';
    pb.style.width = '0%';

    terminalSteps.forEach((step, i) => {
      setTimeout(() => {
        const div = document.createElement('div');
        div.textContent = step.text;
        if (step.status === 1) div.className = 'text-[#37D6A0]';
        if (step.status === 2) div.className = 'text-[#FFBD66]';
        if (i === terminalSteps.length - 1) div.className += ' after:content-[""] after:inline-block after:w-2 after:h-4 after:bg-[#00D9FF] after:ml-1 after:animate-pulse';
        out.appendChild(div);
        pb.style.width = `${((i + 1) / terminalSteps.length) * 100}%`;
      }, fast ? 0 : i * 500);
    });
  };

  // Run on mount
  useEffect(() => {
    // A. Boot dismiss
    const bootTimer = setTimeout(() => {
      setBootOut(true);
      if (h1Ref.current) {
        decryptText(h1Ref.current, 'Sharpen Your Skills. Secure a Safer Tomorrow.');
      }
    }, 1100);

    // B. Hero typing loop
    const heroWords = ['scan demo', 'target lab example', 'checks queued', 'status simulated'];
    let lineIdx = 0;
    let charIdx = 0;
    let currentLines: string[] = [];
    let heroTypingTimer: any = null;

    const stepTyping = () => {
      if (!heroTypingRef.current) return;
      if (lineIdx >= heroWords.length) {
        heroTypingTimer = setTimeout(() => {
          lineIdx = 0;
          charIdx = 0;
          currentLines = [];
          if (heroTypingRef.current) heroTypingRef.current.textContent = '';
          stepTyping();
        }, 2200);
        return;
      }
      const target = heroWords[lineIdx];
      charIdx++;
      heroTypingRef.current.textContent = currentLines.concat(target.slice(0, charIdx)).join('\n');
      if (charIdx >= target.length) {
        currentLines.push(target);
        lineIdx++;
        charIdx = 0;
        heroTypingTimer = setTimeout(stepTyping, 350);
      } else {
        heroTypingTimer = setTimeout(stepTyping, 35);
      }
    };
    stepTyping();

    // C. Background constellation particles
    let animBgId: number;
    const bgCanvas = bgCanvasRef.current;
    if (bgCanvas) {
      const ctx = bgCanvas.getContext('2d');
      let w = (bgCanvas.width = window.innerWidth);
      let h = (bgCanvas.height = window.innerHeight);
      const points: { x: number; y: number; vx: number; vy: number }[] = [];
      const count = window.innerWidth < 768 ? 28 : 55;
      let mx = -999, my = -999;

      for (let i = 0; i < count; i++) {
        points.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35
        });
      }

      const handleResize = () => {
        w = bgCanvas.width = window.innerWidth;
        h = bgCanvas.height = window.innerHeight;
      };
      const handlePointer = (e: PointerEvent) => {
        mx = e.clientX;
        my = e.clientY;
      };

      window.addEventListener('resize', handleResize);
      window.addEventListener('pointermove', handlePointer, { passive: true });

      const renderBg = () => {
        if (!ctx) return;
        ctx.clearRect(0, 0, w, h);

        for (const p of points) {
          p.x += p.vx;
          p.y += p.vy;
          if (p.x < 0 || p.x > w) p.vx *= -1;
          if (p.y < 0 || p.y > h) p.vy *= -1;
          const dx = p.x - mx;
          const dy = p.y - my;
          if (dx * dx + dy * dy < 22000) {
            p.x += dx * 0.005;
            p.y += dy * 0.005;
          }
        }

        for (let i = 0; i < points.length; i++) {
          const a = points[i];
          for (let j = i + 1; j < points.length; j++) {
            const b = points[j];
            const dist = Math.hypot(a.x - b.x, a.y - b.y);
            if (dist < 130) {
              ctx.strokeStyle = `rgba(67, 150, 255, ${(1 - dist / 130) * 0.28})`;
              ctx.beginPath();
              ctx.moveTo(a.x, a.y);
              ctx.lineTo(b.x, b.y);
              ctx.stroke();
            }
          }
          const dm = Math.hypot(a.x - mx, a.y - my);
          if (dm < 180) {
            ctx.strokeStyle = `rgba(0, 217, 255, ${(1 - dm / 180) * 0.6})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(mx, my);
            ctx.stroke();
          }
          ctx.fillStyle = 'rgba(0, 217, 255, 0.7)';
          ctx.fillRect(a.x - 1, a.y - 1, 2, 2);
        }
        animBgId = requestAnimationFrame(renderBg);
      };
      renderBg();
    }

    // D. 3D Wireframe Cyber Globe
    let animGlobeId: number;
    const globeCanvas = globeCanvasRef.current;
    if (globeCanvas) {
      const ctx = globeCanvas.getContext('2d');
      let w = globeCanvas.clientWidth;
      let h = globeCanvas.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      globeCanvas.width = w * dpr;
      globeCanvas.height = h * dpr;
      ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);

      const N = window.innerWidth < 768 ? 220 : 440;
      const P: [number, number, number][] = [];
      for (let i = 0; i < N; i++) {
        const y = 1 - 2 * (i + 0.5) / N;
        const r = Math.sqrt(1 - y * y);
        const a = i * 2.39996;
        P.push([Math.cos(a) * r, y, Math.sin(a) * r]);
      }

      const arcs = [...Array(6)].map((_, k) => ({
        a: (k * 73 + 30) % N,
        b: (k * 157 + 110) % N,
        t: k / 6,
        s: 0.004 + k * 0.0008
      }));

      let ph = 0;
      let mx = 0, my = 0;

      const handleStagePointer = (e: PointerEvent) => {
        if (!globeCanvas) return;
        const b = globeCanvas.getBoundingClientRect();
        mx = (e.clientX - b.left) / b.width - 0.5;
        my = (e.clientY - b.top) / b.height - 0.5;
      };

      const stageEl = stageRef.current;
      stageEl?.addEventListener('pointermove', handleStagePointer);

      const project = (p: [number, number, number], a: number, t: number) => {
        const ca = Math.cos(a), sa = Math.sin(a);
        const X = p[0] * ca + p[2] * sa;
        const Z = -p[0] * sa + p[2] * ca;
        const ct = Math.cos(t), st = Math.sin(t);
        return [X, p[1] * ct - Z * st, p[1] * st + Z * ct];
      };

      const drawGlobe = () => {
        if (!ctx) return;
        ctx.clearRect(0, 0, w, h);
        const R = w * 0.3;
        const cx = w / 2 + mx * 16;
        const cy = h / 2 + my * 16;
        const tl = 0.35 + my * 0.15;
        const sy = Math.sin(ph * 3.2);

        // Core glow
        const g = ctx.createRadialGradient(cx, cy, R * 0.7, cx, cy, R * 1.6);
        g.addColorStop(0, 'rgba(8, 124, 255, 0.22)');
        g.addColorStop(1, 'transparent');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);

        const pts = P.map(p => project(p, ph, tl));

        pts.forEach(q => {
          const bm = Math.abs(q[1] - sy) < 0.07;
          const a = bm ? 1 : 0.15 + 0.6 * (q[2] + 1) / 2;
          ctx.fillStyle = bm ? 'rgba(255, 255, 255, 0.95)' : `rgba(${q[2] > 0 ? '0,217,255' : '8,124,255'},${a})`;
          const s = bm ? 2.6 : 1.7;
          ctx.fillRect(cx + q[0] * R, cy + q[1] * R, s, s);
        });

        // Glowing arcs
        arcs.forEach(arc => {
          const A = pts[arc.a];
          const B = pts[arc.b];
          if (A[2] > -0.1 && B[2] > -0.1) {
            const mx2 = (A[0] + B[0]) / 2 * 1.4;
            const my2 = (A[1] + B[1]) / 2 * 1.4;
            ctx.strokeStyle = 'rgba(0, 217, 255, 0.28)';
            ctx.beginPath();
            ctx.moveTo(cx + A[0] * R, cy + A[1] * R);
            ctx.quadraticCurveTo(cx + mx2 * R, cy + my2 * R, cx + B[0] * R, cy + B[1] * R);
            ctx.stroke();

            const t = arc.t;
            const u = 1 - t;
            const px = u * u * A[0] + 2 * u * t * mx2 + t * t * B[0];
            const py = u * u * A[1] + 2 * u * t * my2 + t * t * B[1];
            ctx.fillStyle = '#fff';
            ctx.shadowColor = '#00D9FF';
            ctx.shadowBlur = 12;
            ctx.beginPath();
            ctx.arc(cx + px * R, cy + py * R, 2.5, 0, 7);
            ctx.fill();
            ctx.shadowBlur = 0;
          }
          arc.t = (arc.t + arc.s) % 1;
        });

        ph += 0.005;
        animGlobeId = requestAnimationFrame(drawGlobe);
      };
      drawGlobe();
    }

    // E. Auth canvas interactive particles
    let animAuthId: number;
    const authCanvas = authCanvasRef.current;
    if (authCanvas) {
      const ctx = authCanvas.getContext('2d');
      let w = (authCanvas.width = authCanvas.clientWidth);
      let h = (authCanvas.height = authCanvas.clientHeight);
      let boost = 0;
      let tgt = 0;
      let pul = 0;

      const N = [...Array(14)].map(() => ({
        x: Math.random() * w,
        y: Math.random() * h * 0.7,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4
      }));

      authPulseRef.current = () => { pul = 1; tgt = 1; setTimeout(() => { tgt = 0; }, 800); };

      const drawAuth = () => {
        if (!ctx) return;
        ctx.clearRect(0, 0, w, h);
        boost += (tgt - boost) * 0.06;
        pul *= 0.97;
        const t = Date.now() / 1000;

        N.forEach(n => {
          n.x += n.vx * (1 + boost * 2);
          n.y += n.vy * (1 + boost * 2);
          if (n.x < 0 || n.x > w) n.vx *= -1;
          if (n.y < 0 || n.y > h * 0.75) n.vy *= -1;
        });

        for (let i = 0; i < N.length; i++) {
          for (let j = i + 1; j < N.length; j++) {
            const a = N[i];
            const b = N[j];
            const d = Math.hypot(a.x - b.x, a.y - b.y);
            if (d < 140 + boost * 60) {
              ctx.strokeStyle = `rgba(0, 217, 255, ${(1 - d / (140 + boost * 60)) * (0.2 + boost * 0.5 + pul * 0.3)})`;
              ctx.beginPath();
              ctx.moveTo(a.x, a.y);
              ctx.lineTo(b.x, b.y);
              ctx.stroke();
              if (boost > 0.3) {
                const u = (t * 0.8 + i * 0.13) % 1;
                ctx.fillStyle = '#fff';
                ctx.fillRect(a.x + (b.x - a.x) * u, a.y + (b.y - a.y) * u, 2.2, 2.2);
              }
            }
          }
        }

        N.forEach(n => {
          ctx.fillStyle = `rgba(0, 217, 255, ${0.6 + boost * 0.4})`;
          ctx.shadowColor = '#00D9FF';
          ctx.shadowBlur = 6 + boost * 10;
          ctx.beginPath();
          ctx.arc(n.x, n.y, 2 + boost * 1.5, 0, 7);
          ctx.fill();
        });
        ctx.shadowBlur = 0;

        animAuthId = requestAnimationFrame(drawAuth);
      };
      drawAuth();
    }

    // F. X-Ray Lens pointer move
    const handleHeroPointer = (e: PointerEvent) => {
      if (!heroRef.current || !xrayRef.current) return;
      const b = heroRef.current.getBoundingClientRect();
      xrayRef.current.style.setProperty('--mx', `${e.clientX - b.left}px`);
      xrayRef.current.style.setProperty('--my', `${e.clientY - b.top}px`);
    };
    const heroEl = heroRef.current;
    heroEl?.addEventListener('pointermove', handleHeroPointer, { passive: true });

    // G. Scroll handler for rail, pipe and file scanner simulation
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? scrollY / docHeight : 0;

      // Rail
      if (railFillRef.current) railFillRef.current.style.height = `${progress * 100}%`;
      if (railBulbRef.current) railBulbRef.current.style.top = `${progress * 100}%`;

      // Active gauge
      const sectionIds = ['top', 'features', 'terminal', 'learning', 'login'];
      let currentSection = 0;
      sectionIds.forEach((id, idx) => {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top < window.innerHeight * 0.45) {
          currentSection = idx;
        }
      });
      setActiveLayer(currentSection);

      // Pipe progress
      if (pipeLineRef.current) {
        const pipeEl = document.getElementById('pipe');
        if (pipeEl) {
          const b = pipeEl.getBoundingClientRect();
          const p = Math.min(1, Math.max(0, (window.innerHeight * 0.75 - b.top) / (b.height + window.innerHeight * 0.2)));
          pipeLineRef.current.style.width = `${p * 100}%`;
        }
      }

      // Scroll-driven File Scanner
      if (scanSectionRef.current) {
        const rc = scanSectionRef.current.getBoundingClientRect();
        const tot = scanSectionRef.current.offsetHeight - window.innerHeight;
        const sp = Math.min(1, Math.max(0, -rc.top / tot));
        const f = sp * scanFiles.length;
        const cur = Math.min(scanFiles.length - 1, Math.floor(f));
        const sub = f - cur;
        const done = sp >= 0.995;

        // Beam & status
        if (scanBeamRef.current) {
          const y = done ? 320 : cur * 44 + sub * 44;
          scanBeamRef.current.style.transform = `translateY(${y}px)`;
          scanBeamRef.current.style.opacity = sp > 0 && !done ? '1' : '0';
        }

        if (scanRingRef.current) {
          scanRingRef.current.style.strokeDashoffset = `${327 * (1 - sp)}`;
        }

        if (scanCurFileRef.current) {
          scanCurFileRef.current.textContent = sp <= 0 ? 'Waiting' : done ? 'Analysis complete' : scanFiles[cur].name;
        }

        if (scanCurStepRef.current) {
          const stepIdx = Math.min(3, Math.floor(sub * 4));
          scanCurStepRef.current.textContent = sp <= 0 ? 'Scroll to begin' : done ? 'All sample files reviewed' : scanStages[stepIdx];
        }

        if (scanWhyRef.current) {
          const stepIdx = Math.min(3, Math.floor(sub * 4));
          scanWhyRef.current.textContent = sp <= 0
            ? 'Keep scrolling down. Each file is checked one at a time, and you will see why it passes or needs attention.'
            : done
            ? 'Finished. Every file now has a result you can read: looks clean, needs review, or sample issue.'
            : stepIdx < 3
            ? scanStageDescriptions[stepIdx]
            : `${scanFiles[cur].name}: ${scanFiles[cur].note}`;
        }

        if (scanVerdictRef.current) {
          scanVerdictRef.current.textContent = done
            ? 'Sample report ready. 3 clean, 3 review items, 2 sample issues flagged.'
            : '';
        }

        // Count meters
        let cleanCnt = 0, revCnt = 0, issCnt = 0;
        for (let i = 0; i <= cur; i++) {
          if (scanFiles[i].status === 'clean') cleanCnt++;
          if (scanFiles[i].status === 'review') revCnt++;
          if (scanFiles[i].status === 'issue') issCnt++;
        }
        if (meterB1Ref.current) meterB1Ref.current.style.width = `${(cleanCnt / scanFiles.length) * 100}%`;
        if (meterB2Ref.current) meterB2Ref.current.style.width = `${(revCnt / scanFiles.length) * 100}%`;
        if (meterB3Ref.current) meterB3Ref.current.style.width = `${(issCnt / scanFiles.length) * 100}%`;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    // Intersection observer for terminal auto-run
    let ranTerminalOnce = false;
    const termEl = terminalOutRef.current;
    if (termEl) {
      const io = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting && !ranTerminalOnce) {
          ranTerminalOnce = true;
          runTerminalDemo();
        }
      }, { threshold: 0.3 });
      io.observe(termEl);
    }

    return () => {
      clearTimeout(bootTimer);
      clearTimeout(heroTypingTimer);
      cancelAnimationFrame(animBgId);
      cancelAnimationFrame(animGlobeId);
      cancelAnimationFrame(animAuthId);
      window.removeEventListener('scroll', handleScroll);
      heroEl?.removeEventListener('pointermove', handleHeroPointer);
    };
  }, []);

  const handleAuthSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes('@')) {
      setAuthError('Enter a valid email address.');
      setAuthSuccess('');
      authPulseRef.current?.();
      return;
    }
    setAuthError('');
    setAuthSuccess('Redirecting to your secure console...');
    authPulseRef.current?.();
    setTimeout(() => {
      navigate('/login');
    }, 700);
  };

  return (
    <div className="bg-[#030712] text-[#F2F7FF] font-sans min-h-screen relative selection:bg-[#00D9FF] selection:text-black">
      {/* 1. Signal Room Boot Screen */}
      {!bootOut && (
        <div
          onClick={() => setBootOut(true)}
          className="fixed inset-0 z-[100] bg-[#030712] grid place-items-center transition-opacity duration-700 cursor-pointer"
        >
          <div className="w-[min(340px,80vw)] text-center text-[13px] text-[#00D9FF] font-mono">
            <svg className="mx-auto mb-4 animate-bounce" width="54" height="62" viewBox="0 0 26 30" fill="none">
              <path d="M13 1 24 5v9c0 7-5 12-11 15C7 26 2 21 2 14V5z" fill="#087CFF" stroke="#00D9FF" strokeWidth="1.5" />
              <path d="m8 15 4 4 7-8" stroke="#fff" strokeWidth="2.4" fill="none" />
            </svg>
            <div className="h-[2px] bg-[rgba(67,150,255,0.2)] my-4 overflow-hidden rounded">
              <div className="h-full bg-[#00D9FF] shadow-[0_0_14px_#00D9FF] animate-[pulse_1s_infinite] w-full" />
            </div>
            INITIALIZING SIGNAL ROOM
            <div className="text-[11px] text-[#6E829F] mt-2">click anywhere to skip</div>
          </div>
        </div>
      )}

      {/* 2. Interactive Constellation Canvas */}
      <canvas ref={bgCanvasRef} className="fixed inset-0 z-0 pointer-events-none opacity-45" />

      {/* 3. Left Rail Indicator */}
      <div className="fixed left-3 top-0 bottom-0 w-[2px] bg-[rgba(67,150,255,0.12)] z-30 hidden lg:block">
        <i ref={railFillRef} className="absolute left-0 top-0 w-full bg-gradient-to-b from-[#087CFF] to-[#00D9FF]" />
        <b
          ref={railBulbRef}
          className="absolute -left-[5px] w-3 h-3 rounded-full bg-[#00D9FF] shadow-[0_0_18px_4px_#00D9FF,0_0_40px_#087CFF] -translate-y-1/2"
        />
      </div>

      {/* 4. Top Header & Nav */}
      <header className="fixed inset-x-0 top-0 z-40 bg-[rgba(3,7,18,0.75)] backdrop-blur-md border-b border-[rgba(67,150,255,0.22)]">
        <nav className="max-w-[1240px] mx-auto flex items-center justify-between px-6 py-3.5 gap-6">
          <Link to="/" className="flex items-center gap-2.5 font-bold text-xl tracking-tight text-white hover:text-[#00D9FF] transition-colors">
            <svg width="26" height="30" viewBox="0 0 26 30" fill="none">
              <path d="M13 1 24 5v9c0 7-5 12-11 15C7 26 2 21 2 14V5z" fill="#087CFF" stroke="#00D9FF" strokeWidth="1.5" />
              <path d="m8 15 4 4 7-8" stroke="#fff" strokeWidth="2.4" fill="none" />
            </svg>
            <span>SecRunner</span>
          </Link>

          <div className="hidden md:flex items-center gap-7 text-sm font-medium text-[#9CB0CA]">
            <a href="#top" className="hover:text-white transition-colors">Home</a>
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#terminal" className="hover:text-white transition-colors">Tools</a>
            <a href="#learning" className="hover:text-white transition-colors">Learning</a>
            <a href="#scan" className="hover:text-white transition-colors">Scan Lab</a>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="px-4 py-2 rounded-lg border border-[rgba(67,150,255,0.22)] text-sm font-medium hover:bg-[rgba(8,124,255,0.15)] hover:border-[#00D9FF] transition-all"
            >
              Login
            </Link>
            <Link
              to="/register"
              className="px-5 py-2 rounded-lg bg-[#087CFF] hover:bg-[#00D9FF] hover:text-black font-semibold text-sm shadow-[0_0_20px_rgba(8,124,255,0.6)] transition-all"
            >
              Get Started
            </Link>
          </div>
        </nav>
      </header>

      {/* 5. Right Floating Gauge */}
      <div className="fixed right-5 top-1/2 -translate-y-1/2 z-30 hidden xl:flex flex-col gap-3.5 text-[11px] font-mono">
        {['ORBIT', 'NETWORK', 'HOST', 'PROCESS', 'AIRLOCK'].map((layer, idx) => (
          <a
            key={layer}
            href={`#${['top', 'features', 'terminal', 'learning', 'login'][idx]}`}
            className={`flex items-center gap-2 justify-end transition-all ${
              activeLayer === idx ? 'text-[#00D9FF] -translate-x-1.5 opacity-100' : 'text-[#9CB0CA] opacity-50 hover:opacity-80'
            }`}
          >
            <span>{layer}</span>
            <i
              className={`w-2 h-2 rounded-full border border-[#00D9FF] block transition-all ${
                activeLayer === idx ? 'bg-[#00D9FF] shadow-[0_0_12px_#00D9FF] scale-125' : ''
              }`}
            />
          </a>
        ))}
      </div>

      <main className="relative z-10">
        {/* 6. Hero Section with Interactive Lens & Cyber Globe */}
        <section
          id="top"
          ref={heroRef}
          className="min-h-screen max-w-[1240px] mx-auto px-6 pt-32 pb-20 grid grid-cols-1 lg:grid-cols-2 items-center gap-12 relative overflow-hidden"
        >
          {/* X-Ray Radar Lens Overlay */}
          <div
            ref={xrayRef}
            className="absolute inset-0 pointer-events-none z-0 bg-[linear-gradient(rgba(0,217,255,0.3)_1px,transparent_1px),linear-gradient(90deg,rgba(0,217,255,0.3)_1px,transparent_1px)] bg-[size:44px_44px] [mask-image:radial-gradient(circle_180px_at_var(--mx,-999px)_var(--my,-999px),#000,transparent)]"
          >
            <span className="absolute left-[8%] top-[22%] text-[10px] font-mono text-[#00D9FF]">NODE ALPHA</span>
            <span className="absolute left-[46%] top-[14%] text-[10px] font-mono text-[#00D9FF]">SECTOR FOUR</span>
            <span className="absolute left-[30%] top-[70%] text-[10px] font-mono text-[#00D9FF]">SECURE LINK OK</span>
            <span className="absolute left-[70%] top-[55%] text-[10px] font-mono text-[#00D9FF]">PACKET FLOW</span>
          </div>

          <div className="relative z-10 space-y-6">
            <h1 ref={h1Ref} className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.08]">
              Sharpen Your Skills. Secure a Safer Tomorrow.
            </h1>
            <p className="text-lg text-[#9CB0CA] max-w-xl leading-relaxed">
              Learn cybersecurity by doing. Explore hands-on security labs, practice real-world scenarios, and build the skills to identify, understand, and respond to security threats.
            </p>
            <div className="flex flex-wrap gap-4 pt-2">
              <a
                href="#learning"
                className="px-6 py-3 rounded-xl bg-[#087CFF] hover:bg-[#00D9FF] hover:text-black font-semibold text-sm shadow-[0_0_24px_rgba(8,124,255,0.6)] transition-all"
              >
                Start Learning
              </a>
              <a
                href="#terminal"
                className="px-6 py-3 rounded-xl border border-[rgba(67,150,255,0.25)] hover:border-[#00D9FF] hover:bg-[rgba(8,124,255,0.12)] text-sm font-semibold transition-all"
              >
                Explore Tools
              </a>
            </div>
          </div>

          {/* 3D Wireframe Cyber Globe & Shield Orbit */}
          <div ref={stageRef} className="relative aspect-square w-full max-w-[540px] mx-auto grid place-items-center">
            <canvas ref={globeCanvasRef} className="absolute inset-0 w-full h-full" />

            {/* Glowing Orbit Rings */}
            <div className="absolute w-[44%] h-[44%] rounded-full border border-dashed border-[rgba(0,217,255,0.45)] animate-[spin_24s_linear_infinite]" />
            <div className="absolute w-[56%] h-[56%] rounded-full border border-dashed border-[rgba(121,91,255,0.45)] animate-[spin_36s_linear_infinite_reverse]" />

            {/* Center Floating Shield */}
            <svg
              className="absolute w-[28%] z-10 filter drop-shadow-[0_0_24px_rgba(0,217,255,0.7)] animate-bounce"
              viewBox="0 0 100 116"
            >
              <defs>
                <linearGradient id="shieldGrad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#00D9FF" />
                  <stop offset="1%" stopColor="#087CFF" />
                </linearGradient>
              </defs>
              <path
                d="M50 3 92 18v36c0 28-19 48-42 59C27 102 8 82 8 54V18z"
                fill="rgba(8,124,255,0.3)"
                stroke="url(#shieldGrad)"
                strokeWidth="3"
              />
              <path d="M50 3v110M8 36h84" stroke="rgba(0,217,255,0.25)" />
              <path d="m30 57 14 14 27-30" stroke="#fff" strokeWidth="7" fill="none" strokeLinecap="round" />
            </svg>

            {/* Telemetry Panels */}
            <div className="absolute left-[-2%] top-[8%] bg-[rgba(10,25,45,0.85)] border border-[rgba(67,150,255,0.22)] rounded-xl p-3 text-xs font-mono backdrop-blur-md min-w-[170px] shadow-lg">
              <span className="text-[10px] text-[#FFBD66] border border-[#FFBD66] px-2 py-0.5 rounded-full inline-block mb-1.5">
                SIMULATION
              </span>
              <div ref={heroTypingRef} className="text-[#00D9FF] whitespace-pre min-h-[3.2em]" />
            </div>

            <div className="absolute right-[-2%] bottom-[10%] bg-[rgba(10,25,45,0.85)] border border-[rgba(67,150,255,0.22)] rounded-xl p-3 text-xs font-mono backdrop-blur-md min-w-[170px] shadow-lg">
              <span className="text-[10px] text-[#37D6A0] border border-[#37D6A0] px-2 py-0.5 rounded-full inline-block mb-1.5">
                ASSURANCE
              </span>
              <div className="text-white">Sample finding</div>
              <div className="text-[#FFBD66]">Medium risk test</div>
            </div>
          </div>
        </section>

        {/* 7. Marquee Banner */}
        <div className="overflow-hidden border-y border-[rgba(67,150,255,0.2)] bg-[rgba(7,17,31,0.6)] py-3 whitespace-nowrap font-mono text-sm text-[#9CB0CA]">
          <div className="inline-block animate-[marquee_28s_linear_infinite]">
            <span className="mx-6 before:content-['◆'] before:text-[#00D9FF] before:mr-3">RECONNAISSANCE</span>
            <span className="mx-6 before:content-['◆'] before:text-[#00D9FF] before:mr-3">ENUMERATION</span>
            <span className="mx-6 before:content-['◆'] before:text-[#00D9FF] before:mr-3">WEB APP SECURITY</span>
            <span className="mx-6 before:content-['◆'] before:text-[#00D9FF] before:mr-3">NETWORK ANALYSIS</span>
            <span className="mx-6 before:content-['◆'] before:text-[#00D9FF] before:mr-3">LOG MONITORING</span>
            <span className="mx-6 before:content-['◆'] before:text-[#00D9FF] before:mr-3">INCIDENT RESPONSE</span>
            <span className="mx-6 before:content-['◆'] before:text-[#00D9FF] before:mr-3">HARDENING</span>
            <span className="mx-6 before:content-['◆'] before:text-[#00D9FF] before:mr-3">REPORTING</span>
          </div>
        </div>

        {/* 8. Feature Node Map & 3D Tilt Cards */}
        <section id="features" className="py-24 max-w-[1240px] mx-auto px-6">
          <div className="space-y-3">
            <h2 className="text-3xl sm:text-5xl font-bold tracking-tight">Every skill is a node on the map.</h2>
            <p className="text-[#9CB0CA] text-lg max-w-2xl">
              Pick a node to explore what it covers. All modules integrate with your live runner and repository audits.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 mt-12 items-center">
            {/* SVG Linked Graph */}
            <div className="relative aspect-square max-w-[480px] w-full mx-auto">
              <svg className="absolute inset-0 w-full h-full overflow-visible" viewBox="0 0 100 100">
                {features.map((f, i) => (
                  <line
                    key={i}
                    x1="50"
                    y1="50"
                    x2={f.x}
                    y2={f.y}
                    stroke="rgba(0,217,255,0.35)"
                    strokeWidth="0.5"
                    strokeDasharray="2,2"
                  />
                ))}
              </svg>

              {/* Central Core Shield */}
              <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 rounded-full bg-[rgba(8,124,255,0.25)] border border-[#00D9FF] grid place-items-center shadow-[0_0_20px_#00D9FF]">
                <svg width="24" height="28" viewBox="0 0 26 30" fill="none">
                  <path d="M13 1 24 5v9c0 7-5 12-11 15C7 26 2 21 2 14V5z" fill="#087CFF" stroke="#00D9FF" strokeWidth="1.5" />
                </svg>
              </div>

              {/* Orbiting Clickable Nodes */}
              {features.map((f, i) => (
                <button
                  key={i}
                  onClick={() => setSelectedFeature(i)}
                  style={{ left: `${f.x}%`, top: `${f.y}%` }}
                  className={`absolute -translate-x-1/2 -translate-y-1/2 px-3.5 py-1.5 rounded-full text-xs font-medium border transition-all ${
                    selectedFeature === i
                      ? 'bg-[#0f2440] border-[#00D9FF] text-[#00D9FF] shadow-[0_0_24px_rgba(0,217,255,0.5)] scale-110'
                      : 'bg-[#0B1728] border-[rgba(67,150,255,0.25)] text-[#F2F7FF] hover:border-[#00D9FF]'
                  }`}
                >
                  {f.title}
                </button>
              ))}
            </div>

            {/* Selected Detail Panel */}
            <div className="bg-[rgba(10,25,45,0.78)] border border-[rgba(67,150,255,0.22)] rounded-2xl p-8 backdrop-blur-md shadow-2xl">
              <span className="text-xs font-semibold px-3 py-1 rounded-full border border-[#FFBD66] text-[#FFBD66]">
                Operational Module
              </span>
              <h3 className="text-2xl font-bold text-white mt-4 mb-2">{features[selectedFeature].title}</h3>
              <p className="text-[#9CB0CA] leading-relaxed mb-6">{features[selectedFeature].desc}</p>
              <a
                href="#terminal"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-[#00D9FF] text-[#00D9FF] hover:bg-[#00D9FF] hover:text-black text-sm font-semibold transition-all"
              >
                See the simulation →
              </a>
            </div>
          </div>

          {/* 4 Conic Glow 3D Tilt Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-16">
            {[
              {
                title: 'Guided labs',
                desc: 'Step-by-step exercises in a contained sandbox.',
                icon: (
                  <path d="M4 17l6-6-6-6M12 19h8" stroke="#00D9FF" strokeWidth="2" strokeLinecap="round" />
                )
              },
              {
                title: 'Learning paths',
                desc: 'Beginner to advanced, in a structured curriculum.',
                icon: (
                  <circle cx="12" cy="12" r="9" stroke="#00D9FF" strokeWidth="2" fill="none" />
                )
              },
              {
                title: 'Test runner',
                desc: '35 automated checks with instant plain-language reports.',
                icon: (
                  <path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z" stroke="#00D9FF" strokeWidth="2" fill="none" />
                )
              },
              {
                title: 'Practical tools',
                desc: 'Hands-on utilities for everyday production posture.',
                icon: (
                  <path d="M14 7l3-3 3 3-3 3M3 21l9-9M12 12l2 2" stroke="#00D9FF" strokeWidth="2" strokeLinecap="round" />
                )
              }
            ].map((card, idx) => (
              <div
                key={idx}
                className="relative bg-[#0B1728] border border-[rgba(67,150,255,0.22)] hover:border-[#00D9FF] rounded-2xl p-6 transition-all hover:-translate-y-1 hover:shadow-[0_12px_36px_rgba(0,217,255,0.15)] group"
              >
                <div className="w-10 h-10 rounded-xl bg-[rgba(0,217,255,0.1)] grid place-items-center mb-4 group-hover:scale-110 transition-transform">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    {card.icon}
                  </svg>
                </div>
                <h3 className="text-xl font-bold mb-2 text-white">{card.title}</h3>
                <p className="text-sm text-[#9CB0CA] leading-relaxed mb-4">{card.desc}</p>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded border border-[rgba(67,150,255,0.3)] text-[#00D9FF]">
                  Live Ready
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* 9. Scripted Terminal Scan Demo */}
        <section id="terminal" className="py-24 max-w-[1240px] mx-auto px-6">
          <div className="space-y-3">
            <h2 className="text-3xl sm:text-5xl font-bold tracking-tight">Watch a harmless scan run.</h2>
            <p className="text-[#9CB0CA] text-lg max-w-2xl">
              A scripted demonstration simulating how SecRunner monitors endpoints, validates configurations, and reports telemetry.
            </p>
          </div>

          <div className="mt-10 bg-[#050c18] border border-[rgba(67,150,255,0.25)] rounded-2xl overflow-hidden shadow-[0_20px_60px_rgba(0,100,255,0.15)]">
            <div className="flex items-center justify-between px-5 py-3 border-b border-[rgba(67,150,255,0.22)] font-mono text-xs text-[#9CB0CA]">
              <span className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#00D9FF] animate-ping" />
                secrunner lab scan demo
              </span>
              <span className="px-2 py-0.5 rounded border border-[#FFBD66] text-[#FFBD66]">SIMULATION</span>
            </div>

            <div className="h-[2px] bg-[rgba(67,150,255,0.15)]">
              <i ref={terminalProgressRef} className="block h-full w-0 bg-gradient-to-r from-[#087CFF] to-[#00D9FF] shadow-[0_0_10px_#00D9FF] transition-all duration-300" />
            </div>

            <div className="relative p-6 font-mono text-sm leading-relaxed text-[#bcd6ff] min-h-[260px] max-h-[360px] overflow-y-auto">
              <pre ref={terminalOutRef} className="whitespace-pre-wrap" />
              <div className="absolute inset-x-0 h-16 bg-gradient-to-b from-transparent via-[rgba(0,217,255,0.1)] to-transparent pointer-events-none animate-[scanline_3s_linear_infinite]" />
            </div>

            <div className="flex flex-wrap items-center gap-4 px-5 py-3.5 border-t border-[rgba(67,150,255,0.22)] bg-[#030712]">
              <button
                onClick={() => runTerminalDemo(false)}
                className="px-4 py-2 rounded-lg bg-[#087CFF] hover:bg-[#00D9FF] hover:text-black text-xs font-semibold shadow-[0_0_15px_rgba(8,124,255,0.5)] transition-all"
              >
                Replay Demo
              </button>
              <button
                onClick={() => runTerminalDemo(true)}
                className="px-4 py-2 rounded-lg border border-[rgba(67,150,255,0.25)] hover:border-[#00D9FF] text-xs font-semibold transition-all"
              >
                Skip to End
              </button>
              <small className="text-xs text-[#9CB0CA] ml-auto">Predefined output with a reserved example target</small>
            </div>
          </div>
        </section>

        {/* 10. Scroll-driven File Scanner Simulation */}
        <section id="scan" ref={scanSectionRef} className="py-24 max-w-[1240px] mx-auto px-6">
          <div className="space-y-3 mb-10">
            <h2 className="text-3xl sm:text-5xl font-bold tracking-tight">Scroll to scan the files.</h2>
            <p className="text-[#9CB0CA] text-lg max-w-2xl">
              Scroll down to watch a sample project get scanned and analyzed file by file with automated vulnerability heuristics.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
            {/* File List */}
            <div className="relative bg-[#050c18] border border-[rgba(67,150,255,0.22)] rounded-2xl p-4 overflow-hidden">
              <div
                ref={scanBeamRef}
                className="absolute inset-x-0 top-0 h-12 bg-gradient-to-b from-transparent via-[rgba(0,217,255,0.3)] to-transparent border-y border-[rgba(0,217,255,0.6)] pointer-events-none transition-transform duration-100"
              />
              <div className="space-y-2">
                {scanFiles.map((file, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 rounded-lg bg-[rgba(11,23,40,0.5)] border border-[rgba(67,150,255,0.12)] text-sm"
                  >
                    <span className="font-mono text-white">{file.name}</span>
                    <span
                      className={`text-xs font-semibold px-2 py-0.5 rounded ${
                        file.status === 'clean'
                          ? 'text-[#37D6A0] bg-[rgba(55,214,160,0.1)]'
                          : file.status === 'review'
                          ? 'text-[#FFBD66] bg-[rgba(255,189,102,0.1)]'
                          : 'text-[#ff8a9a] bg-[rgba(255,82,107,0.1)]'
                      }`}
                    >
                      {file.status === 'clean' ? 'Looks clean' : file.status === 'review' ? 'Needs review' : 'Sample issue'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Analysis Telemetry */}
            <div className="bg-[rgba(10,25,45,0.78)] border border-[rgba(67,150,255,0.22)] rounded-2xl p-6 backdrop-blur-md flex flex-col gap-6">
              <div className="flex items-center justify-between border-b border-[rgba(67,150,255,0.15)] pb-3">
                <span className="font-mono text-xs text-[#00D9FF]">analysis engine</span>
                <span className="text-[10px] border border-[#FFBD66] text-[#FFBD66] px-2 py-0.5 rounded">SIMULATION</span>
              </div>

              <div className="flex items-center gap-6">
                <svg className="w-24 h-24 -rotate-90" viewBox="0 0 120 120">
                  <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(67,150,255,0.2)" strokeWidth="8" />
                  <circle
                    ref={scanRingRef}
                    cx="60"
                    cy="60"
                    r="52"
                    fill="none"
                    stroke="#00D9FF"
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray="327"
                    strokeDashoffset="327"
                    className="filter drop-shadow-[0_0_6px_#00D9FF] transition-all duration-300"
                  />
                </svg>
                <div>
                  <div ref={scanCurFileRef} className="text-xl font-bold text-white font-mono">
                    Waiting
                  </div>
                  <div ref={scanCurStepRef} className="text-sm text-[#9CB0CA]">
                    Scroll to begin
                  </div>
                </div>
              </div>

              <div ref={scanWhyRef} className="p-4 rounded-xl border-l-4 border-[#00D9FF] bg-[rgba(0,217,255,0.08)] text-sm leading-relaxed text-slate-200 min-h-[4.5em]">
                Keep scrolling down. Each file is checked one at a time, and you will see why it passes or needs attention.
              </div>

              <div className="space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[#37D6A0]">Looks clean</span>
                  <div className="w-48 h-2 bg-[rgba(67,150,255,0.15)] rounded-full overflow-hidden">
                    <i ref={meterB1Ref} className="block h-full bg-[#37D6A0] transition-all duration-300 w-0" />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#FFBD66]">Needs review</span>
                  <div className="w-48 h-2 bg-[rgba(67,150,255,0.15)] rounded-full overflow-hidden">
                    <i ref={meterB2Ref} className="block h-full bg-[#FFBD66] transition-all duration-300 w-0" />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#FF526B]">Sample issue</span>
                  <div className="w-48 h-2 bg-[rgba(67,150,255,0.15)] rounded-full overflow-hidden">
                    <i ref={meterB3Ref} className="block h-full bg-[#FF526B] transition-all duration-300 w-0" />
                  </div>
                </div>
              </div>

              <div ref={scanVerdictRef} className="text-xs text-[#9CB0CA] min-h-[2em]" />
            </div>
          </div>
        </section>

        {/* 11. Pipeline Process */}
        <section id="learning" className="py-24 max-w-[1240px] mx-auto px-6">
          <h2 className="text-3xl sm:text-5xl font-bold tracking-tight mb-12">Learn it. Break it safely. Do it better.</h2>
          <div id="pipe" className="relative grid grid-cols-1 md:grid-cols-3 gap-8 pt-8">
            <div className="absolute top-0 inset-x-0 h-[2px] bg-[rgba(67,150,255,0.2)] hidden md:block">
              <i ref={pipeLineRef} className="block h-full w-0 bg-gradient-to-r from-[#087CFF] to-[#00D9FF] shadow-[0_0_14px_#00D9FF]" />
            </div>

            {[
              { title: 'Learn', desc: 'Understand attack surfaces, defensive principles and the tools professionals use.' },
              { title: 'Practice', desc: 'Apply each idea in an authorized, controlled environment built for learning.' },
              { title: 'Improve', desc: 'Review results, close knowledge gaps and track compliance metrics in your portal.' }
            ].map((st, i) => (
              <div key={i} className="relative pt-6 space-y-3">
                <span className="w-5 h-5 rounded-full bg-[#00D9FF] shadow-[0_0_16px_#00D9FF] block" />
                <h3 className="text-2xl font-bold text-white">{st.title}</h3>
                <p className="text-[#9CB0CA] leading-relaxed text-sm">{st.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* 12. Interactive Auth Airlock */}
        <section id="login" className="py-24 max-w-[1240px] mx-auto px-6">
          <div className="space-y-3 mb-10">
            <h2 className="text-3xl sm:text-5xl font-bold tracking-tight">The quiet airlock.</h2>
            <p className="text-[#9CB0CA] text-lg max-w-2xl">
              A high-security gateway into your SecRunner workspace. Sign in to review past audits, configure target endpoints, or trigger automated scans.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 rounded-2xl border border-[rgba(67,150,255,0.22)] bg-[#07111F] overflow-hidden shadow-2xl">
            <div className="relative p-10 min-h-[380px] bg-gradient-to-b from-[#050d1c] to-[#07111F] flex flex-col justify-between overflow-hidden">
              <canvas ref={authCanvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />
              <div className="relative z-10">
                <span className="text-xs font-mono px-3 py-1 rounded-full border border-[#00D9FF] text-[#00D9FF]">
                  SECURE PORTAL
                </span>
                <h3 className="text-3xl font-bold text-white mt-6 mb-2">
                  Secure Access.<br />A Smarter Way to Learn.
                </h3>
                <p className="text-sm text-[#9CB0CA]">Sign in to pick up where you left off.</p>
              </div>
              <div className="relative z-10 pt-8">
                <Link to="/register" className="text-sm text-[#00D9FF] hover:underline">
                  Don't have an account yet? Create one here →
                </Link>
              </div>
            </div>

            <form onSubmit={handleAuthSubmit} className="p-10 flex flex-col justify-center space-y-5 bg-[#030712]">
              <h3 className="text-2xl font-bold text-white">Welcome back</h3>
              <div>
                <label className="block text-xs font-mono text-[#9CB0CA] mb-1.5">Email address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  onFocus={() => authPulseRef.current?.()}
                  className="w-full bg-[#0B1728] border border-[rgba(67,150,255,0.25)] rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-[#00D9FF] focus:ring-1 focus:ring-[#00D9FF] transition-all text-sm"
                  placeholder="name@company.com"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-[#9CB0CA] mb-1.5">Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  onFocus={() => authPulseRef.current?.()}
                  className="w-full bg-[#0B1728] border border-[rgba(67,150,255,0.25)] rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-[#00D9FF] focus:ring-1 focus:ring-[#00D9FF] transition-all text-sm"
                  placeholder="••••••••"
                />
              </div>

              {authError && <div className="text-sm text-[#FF526B] font-mono">{authError}</div>}
              {authSuccess && <div className="text-sm text-[#37D6A0] font-mono">{authSuccess}</div>}

              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-[#087CFF] hover:bg-[#00D9FF] hover:text-black font-semibold text-sm shadow-[0_0_20px_rgba(8,124,255,0.5)] transition-all"
              >
                Sign in to Dashboard
              </button>

              <div className="flex items-center justify-between pt-2 text-xs text-[#9CB0CA]">
                <Link to="/login" className="hover:text-white transition-colors">
                  Direct Login Form
                </Link>
                <Link to="/register" className="hover:text-white transition-colors">
                  Create New Account
                </Link>
              </div>
            </form>
          </div>
        </section>

        {/* 13. Final Call to Action */}
        <section className="py-24 text-center max-w-[1240px] mx-auto px-6">
          <div className="w-20 h-20 mx-auto mb-6 relative">
            <div className="absolute inset-0 rounded-full border border-[#00D9FF] animate-ping opacity-30" />
            <svg className="w-full h-full filter drop-shadow-[0_0_20px_#00D9FF]" viewBox="0 0 26 30" fill="none">
              <path d="M13 1 24 5v9c0 7-5 12-11 15C7 26 2 21 2 14V5z" fill="#087CFF" stroke="#00D9FF" strokeWidth="1.5" />
              <path d="m8 15 4 4 7-8" stroke="#fff" strokeWidth="2.4" fill="none" />
            </svg>
          </div>

          <h2 className="text-3xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-4">
            Your Security Journey Starts Here.
          </h2>
          <p className="text-lg text-[#9CB0CA] max-w-xl mx-auto mb-8">
            Learn. Practice. Test. Improve. Full visibility across your entire software supply chain.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/register"
              className="px-8 py-3.5 rounded-xl bg-[#087CFF] hover:bg-[#00D9FF] hover:text-black font-semibold text-sm shadow-[0_0_28px_rgba(8,124,255,0.6)] transition-all"
            >
              Get Started Now
            </Link>
            <a
              href="#features"
              className="px-8 py-3.5 rounded-xl border border-[rgba(67,150,255,0.25)] hover:border-[#00D9FF] hover:bg-[rgba(8,124,255,0.12)] text-sm font-semibold transition-all"
            >
              Explore Capabilities
            </a>
          </div>
        </section>
      </main>

      {/* 14. Footer */}
      <footer className="border-t border-[rgba(67,150,255,0.2)] py-8 text-center text-sm text-[#9CB0CA] bg-[#030712]">
        <div className="max-w-[1240px] mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#37D6A0]" />
            <span>SecRunner Security Platform &bull; Powered by Vovalyx Sentinel</span>
          </div>
          <div>All automated diagnostics and interactive modules live and protected.</div>
        </div>
      </footer>
    </div>
  );
}
