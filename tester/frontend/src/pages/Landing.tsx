import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../config';

export default function Landing() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  // Handle direct sign in from the airlock form
  const handleAirlockSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');

    const cleanEmail = email.trim();
    if (!cleanEmail || !/^\S+@\S+\.\S+$/.test(cleanEmail)) {
      setAuthError('Please enter a valid email address.');
      return;
    }
    if (!password) {
      setAuthError('Password is required.');
      return;
    }

    setIsLoggingIn(true);
    try {
      const formData = new URLSearchParams();
      formData.append('username', cleanEmail);
      formData.append('password', password);

      const res = await apiClient.post('/auth/login', formData);
      localStorage.setItem('access_token', res.data.access_token);
      navigate('/dashboard');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setAuthError(typeof detail === 'string' ? detail : 'Sign in failed. Check your credentials.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  useEffect(() => {
    // Inject HTML 'js' class
    document.documentElement.classList.add('js');

    const RM = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const SL = [..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"];

    function dec(el: HTMLElement, done?: () => void) {
      const t = el.dataset.t || (el.dataset.t = el.textContent || '');
      if (RM) {
        el.textContent = t;
        return;
      }
      el.setAttribute('aria-label', t);
      let f = 0, T = 30;
      const id = setInterval(() => {
        f++;
        el.textContent = [...t]
          .map((c, i) => (c === ' ' || i < (f * t.length) / T ? c : SL[(Math.random() * SL.length) | 0]))
          .join('');
        if (f >= T) {
          el.textContent = t;
          clearInterval(id);
          done && done();
        }
      }, 24);
    }

    // Boot sequence
    const boot = document.getElementById('boot');
    let started = false;
    function go() {
      if (started || !boot) return;
      started = true;
      boot.classList.add('out');
      const h1 = document.getElementById('h1');
      if (h1) dec(h1);
      typeHero();
    }
    if (boot) boot.onclick = go;
    const bootTimer = setTimeout(go, RM ? 0 : 1200);

    // Reveal + wipe + decrypt headings
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((x) => {
          if (x.isIntersecting) {
            x.target.classList.add('in');
            x.target.querySelectorAll &&
              x.target.querySelectorAll('[data-d]').forEach((h: any) => dec(h));
            if ((x.target as HTMLElement).matches('[data-d]')) dec(x.target as HTMLElement);
            io.unobserve(x.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    document.querySelectorAll('.rv,.sec').forEach((n) => io.observe(n));
    const revealTimer = setTimeout(() => document.querySelectorAll('.rv').forEach((n) => n.classList.add('in')), 3500);

    // Pointer: Xray lens, magnetic buttons, tilt cards
    const hero = document.querySelector('.hero') as HTMLElement;
    const xr = document.querySelector('.xray') as HTMLElement;
    const onPointerMove = (e: PointerEvent) => {
      if (!hero || !xr) return;
      const b = hero.getBoundingClientRect();
      xr.style.setProperty('--mx', `${e.clientX - b.left}px`);
      xr.style.setProperty('--my', `${e.clientY - b.top}px`);
    };
    window.addEventListener('pointermove', onPointerMove, { passive: true });

    if (!RM && window.matchMedia('(hover:hover)').matches) {
      document.querySelectorAll('.mag').forEach((b: any) => {
        b.onpointermove = (e: PointerEvent) => {
          const r = b.getBoundingClientRect();
          b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.18}px,${(e.clientY - r.top - r.height / 2) * 0.28}px)`;
        };
        b.onpointerleave = () => (b.style.transform = '');
      });

      document.querySelectorAll('[data-tilt]').forEach((c: any) => {
        c.onpointermove = (e: PointerEvent) => {
          const r = c.getBoundingClientRect();
          const x = (e.clientX - r.left) / r.width;
          const y = (e.clientY - r.top) / r.height;
          c.style.transform = `rotateY(${(x - 0.5) * 16}deg) rotateX(${(0.5 - y) * 16}deg) translateY(-6px)`;
          c.style.setProperty('--px', `${x * 100}%`);
          c.style.setProperty('--py', `${y * 100}%`);
        };
        c.onpointerleave = () => (c.style.transform = '');
      });
    }

    // Hero panel typing loop
    let heroTypingTimeout: any;
    function typeHero() {
      const el = document.getElementById('ht');
      if (!el) return;
      const L = ['scan demo', 'target lab example', 'checks queued', 'status simulated'];
      if (RM) {
        el.textContent = L.join('\n');
        return;
      }
      let li = 0, ci = 0, buf: string[] = [];
      function s() {
        if (!el) return;
        if (li >= L.length) {
          heroTypingTimeout = setTimeout(() => {
            li = 0; ci = 0; buf = [];
            el.textContent = '';
            s();
          }, 2400);
          return;
        }
        const l = L[li];
        ci++;
        el.textContent = buf.concat(l.slice(0, ci)).join('\n');
        if (ci >= l.length) {
          buf.push(l);
          li++;
          ci = 0;
          heroTypingTimeout = setTimeout(s, 380);
        } else {
          heroTypingTimeout = setTimeout(s, 38);
        }
      }
      s();
    }

    // Network background canvas (#bg)
    let bgRaf: number;
    (function initBgCanvas() {
      const c = document.getElementById('bg') as HTMLCanvasElement;
      if (!c) return;
      const x = c.getContext('2d');
      if (!x) return;
      let W: number, H: number, P: any[] = [], mx = -999, my = -999, vis = true;

      function rs() {
        if (!c) return;
        W = c.width = window.innerWidth;
        H = c.height = window.innerHeight;
        const N = W < 700 ? 22 : 44;
        P = [];
        for (let i = 0; i < N; i++) {
          P.push({
            x: Math.random() * W,
            y: Math.random() * H,
            vx: (Math.random() - 0.5) * 0.35,
            vy: (Math.random() - 0.5) * 0.35,
          });
        }
      }
      rs();
      window.addEventListener('resize', rs);

      const moveHandler = (e: PointerEvent) => {
        mx = e.clientX;
        my = e.clientY;
      };
      window.addEventListener('pointermove', moveHandler, { passive: true });

      let lt = 0;
      function f(ts: number) {
        if (!vis) return;
        if (!RM && ts && ts - lt < 30) {
          bgRaf = requestAnimationFrame(f);
          return;
        }
        lt = ts || 0;
        x?.clearRect(0, 0, W, H);

        for (const p of P) {
          p.x += p.vx;
          p.y += p.vy;
          if (p.x < 0 || p.x > W) p.vx *= -1;
          if (p.y < 0 || p.y > H) p.vy *= -1;
          const dx = p.x - mx, dy = p.y - my;
          if (dx * dx + dy * dy < 22000) {
            p.x += dx * 0.006;
            p.y += dy * 0.006;
          }
        }

        for (let i = 0; i < P.length; i++) {
          const a = P[i];
          for (let j = i + 1; j < P.length; j++) {
            const b = P[j], ddx = a.x - b.x, ddy = a.y - b.y, d2 = ddx * ddx + ddy * ddy;
            if (d2 < 18225 && x) {
              const d = Math.sqrt(d2);
              x.strokeStyle = `rgba(67,150,255,${(1 - d / 135) * 0.32})`;
              x.beginPath();
              x.moveTo(a.x, a.y);
              x.lineTo(b.x, b.y);
              x.stroke();
            }
          }
          if (x) {
            const dm = Math.hypot(a.x - mx, a.y - my);
            if (dm < 190) {
              x.strokeStyle = `rgba(0,217,255,${(1 - dm / 190) * 0.8})`;
              x.beginPath();
              x.moveTo(a.x, a.y);
              x.lineTo(mx, my);
              x.stroke();
            }
            x.fillStyle = 'rgba(0,217,255,.7)';
            x.fillRect(a.x - 1, a.y - 1, 2, 2);
          }
        }
        if (!RM) bgRaf = requestAnimationFrame(f);
      }
      f(0);
    })();

    // 3D Particle Globe (#globe)
    let globeRaf: number;
    (function initGlobe() {
      const c = document.getElementById('globe') as HTMLCanvasElement;
      const st = document.getElementById('stage') as HTMLElement;
      if (!c || !st) return;
      const x = c.getContext('2d');
      if (!x) return;

      let W: number, H: number, P: number[][] = [], N = window.innerWidth < 700 ? 220 : 380, ph = 0, vis = true, mx = 0, my = 0;

      for (let i = 0; i < N; i++) {
        const y = 1 - (2 * (i + 0.5)) / N;
        const r = Math.sqrt(1 - y * y);
        const a = i * 2.39996;
        P.push([Math.cos(a) * r, y, Math.sin(a) * r]);
      }

      const arcs = [...Array(7)].map((_, k) => ({
        a: (k * 97 + 40) % N,
        b: (k * 211 + 160) % N,
        t: k / 7,
        s: 0.004 + k * 0.0009,
      }));

      function rs() {
        if (!c || !x) return;
        const d = Math.min(1.5, window.devicePixelRatio || 1);
        W = c.clientWidth;
        H = c.clientHeight;
        c.width = W * d;
        c.height = H * d;
        x.setTransform(d, 0, 0, d, 0, 0);
      }
      rs();
      window.addEventListener('resize', rs);

      st.onpointermove = (e: PointerEvent) => {
        const b = c.getBoundingClientRect();
        mx = (e.clientX - b.left) / b.width - 0.5;
        my = (e.clientY - b.top) / b.height - 0.5;
      };

      function pr(p: number[], a: number, t: number) {
        const ca = Math.cos(a), sa = Math.sin(a);
        const X = p[0] * ca + p[2] * sa;
        const Z = -p[0] * sa + p[2] * ca;
        const ct = Math.cos(t), s2 = Math.sin(t);
        return [X, p[1] * ct - Z * s2, p[1] * s2 + Z * ct];
      }

      const onScrollGlobe = () => {
        const s = Math.min(1, window.scrollY / window.innerHeight);
        if (st) {
          st.style.transform = `translateY(${-s * 70}px) scale(${1 + s * 0.55}) rotate(${s * 14}deg)`;
          st.style.opacity = `${1 - s * 0.95}`;
        }
      };
      window.addEventListener('scroll', onScrollGlobe, { passive: true });

      function draw() {
        if (!vis || !x) return;
        x.clearRect(0, 0, W, H);
        const R = W * 0.3;
        const cx = W / 2 + mx * 18;
        const cy = H / 2 + my * 18;
        const tl = 0.35 + my * 0.15;
        const sy = Math.sin(ph * 3.2);

        const g = x.createRadialGradient(cx, cy, R * 0.8, cx, cy, R * 1.7);
        g.addColorStop(0, 'rgba(8,124,255,.22)');
        g.addColorStop(1, 'transparent');
        x.fillStyle = g;
        x.fillRect(0, 0, W, H);

        const pts = P.map((p) => pr(p, ph, tl));
        pts.forEach((q) => {
          const bm = Math.abs(q[1] - sy) < 0.07;
          const a = bm ? 1 : 0.15 + (0.6 * (q[2] + 1)) / 2;
          x.fillStyle = bm ? '#fff' : q[2] > 0 ? '#00D9FF' : '#087CFF';
          x.globalAlpha = bm ? 1 : a;
          const s = bm ? 2.8 : 1.8;
          x.fillRect(cx + q[0] * R, cy + q[1] * R, s, s);
        });
        x.globalAlpha = 1;

        arcs.forEach((r) => {
          const A = pts[r.a], B = pts[r.b];
          if (A[2] > -0.1 && B[2] > -0.1) {
            const mx2 = ((A[0] + B[0]) / 2) * 1.4;
            const my2 = ((A[1] + B[1]) / 2) * 1.4;
            x.strokeStyle = 'rgba(0,217,255,.3)';
            x.beginPath();
            x.moveTo(cx + A[0] * R, cy + A[1] * R);
            x.quadraticCurveTo(cx + mx2 * R, cy + my2 * R, cx + B[0] * R, cy + B[1] * R);
            x.stroke();
            const t = r.t, u = 1 - t;
            const px = u * u * A[0] + 2 * u * t * mx2 + t * t * B[0];
            const py = u * u * A[1] + 2 * u * t * my2 + t * t * B[1];
            x.fillStyle = 'rgba(0,217,255,.35)';
            x.beginPath();
            x.arc(cx + px * R, cy + py * R, 6, 0, 7);
            x.fill();
            x.fillStyle = '#fff';
            x.beginPath();
            x.arc(cx + px * R, cy + py * R, 2.6, 0, 7);
            x.fill();
          }
          r.t = (r.t + r.s) % 1;
        });

        [[1.3, -0.35, 0.28, 1], [1.55, 0.2, 0.3, -1.4]].forEach((o, i) => {
          x.save();
          x.translate(cx, cy);
          x.rotate(o[1]);
          x.strokeStyle = i ? 'rgba(121,91,255,.45)' : 'rgba(0,217,255,.35)';
          x.beginPath();
          x.ellipse(0, 0, R * o[0], R * o[0] * o[2], 0, 0, 7);
          x.stroke();
          const an = ph * 2.2 * o[3] + i * 2;
          x.fillStyle = i ? '#795BFF' : '#00D9FF';
          x.beginPath();
          x.arc(Math.cos(an) * R * o[0], Math.sin(an) * R * o[0] * o[2], 4, 0, 7);
          x.fill();
          x.restore();
        });

        if (!RM) {
          ph += 0.005;
          globeRaf = requestAnimationFrame(draw);
        }
      }
      draw();
    })();

    // Interactive Map Nodes
    (function initMap() {
      const F: [string, number, number, string][] = [
        ['Penetration Testing', 50, 8, 'Learn how attackers find weaknesses so you can find them first, using authorized lab targets only.'],
        ['Network Security', 88, 28, 'Explore firewalls, scanning and traffic analysis in a contained environment.'],
        ['Web App Security', 88, 72, 'Study injection, authentication and access-control flaws in practice apps.'],
        ['Vulnerability Assessment', 50, 92, 'Practice prioritizing findings and writing clear, understandable reports.'],
        ['SIEM and Monitoring', 12, 72, 'Read logs, spot patterns and understand how detection works.'],
        ['Incident Response', 12, 28, 'Rehearse the steps from first alert to recovery.'],
      ];
      const g = document.getElementById('graph');
      const L = document.getElementById('lines');
      const dt = document.getElementById('dt');
      const dd = document.getElementById('dd');
      const det = document.getElementById('det');
      if (!g || !L || !dt || !dd || !det) return;

      const ns = 'http://www.w3.org/2000/svg';
      const B: HTMLButtonElement[] = [];

      L.innerHTML = '';
      F.forEach((f, i) => {
        const l = document.createElementNS(ns, 'line');
        ['x1', 'y1'].forEach((k) => l.setAttribute(k, '50'));
        l.setAttribute('x2', String(f[1]));
        l.setAttribute('y2', String(f[2]));
        l.setAttribute('stroke', 'rgba(0,217,255,.4)');
        l.setAttribute('stroke-width', '.4');
        l.setAttribute('vector-effect', 'non-scaling-stroke');
        L.appendChild(l);

        const c = document.createElementNS(ns, 'circle');
        c.setAttribute('r', '1.1');
        c.setAttribute('fill', '#fff');
        if (!RM) {
          const a = document.createElementNS(ns, 'animate'), b = a.cloneNode() as Element;
          a.setAttribute('attributeName', 'cx');
          a.setAttribute('values', `50;${f[1]}`);
          b.setAttribute('attributeName', 'cy');
          b.setAttribute('values', `50;${f[2]}`);
          [a, b].forEach((z) => {
            z.setAttribute('dur', `${2.2 + i * 0.35}s`);
            z.setAttribute('repeatCount', 'indefinite');
            c.appendChild(z);
          });
        } else {
          c.setAttribute('cx', String(f[1]));
          c.setAttribute('cy', String(f[2]));
        }
        L.appendChild(c);

        const btn = document.createElement('button');
        btn.className = 'node';
        btn.type = 'button';
        btn.textContent = f[0];
        btn.style.left = `${f[1]}%`;
        btn.style.top = `${f[2]}%`;
        btn.style.animationDelay = `${-i * 0.8}s`;
        btn.setAttribute('aria-pressed', 'false');

        btn.onclick = btn.onfocus = () => {
          B.forEach((z) => z.setAttribute('aria-pressed', 'false'));
          btn.setAttribute('aria-pressed', 'true');
          dt.textContent = f[0];
          dd.textContent = f[3];
          det.classList.remove('sw');
          void det.offsetWidth;
          if (!RM) det.classList.add('sw');
        };

        btn.onkeydown = (e) => {
          const d = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
          if (d) {
            e.preventDefault();
            B[(i + d + B.length) % B.length].focus();
          }
        };

        g.appendChild(btn);
        B.push(btn);
      });

      if (B[0]) B[0].click();
    })();

    // Simulated Terminal
    (function initTerminal() {
      const S: [string, number][] = [
        ['Initializing lab environment', 0],
        ['Environment ready, sandboxed and offline', 1],
        ['Target lab example test', 0],
        ['Starting sample test suite', 0],
        ['Header checks ok', 1],
        ['Port exposure ok', 1],
        ['Cookie flags, one sample warning', 2],
        ['Input handling ok', 1],
        ['Suite complete. Three passed, one sample warning.', 1],
        ['This was scripted output. No real system was scanned.', 0],
      ];
      const o = document.getElementById('out');
      const pb = document.getElementById('pb');
      const run = document.getElementById('run');
      const sk = document.getElementById('skip');
      const lv = document.getElementById('live');
      if (!o || !pb || !run || !sk) return;

      let tm: any[] = [];
      function add(s: [string, number], i: number) {
        if (!o || !pb) return;
        const d = document.createElement('div');
        d.textContent = s[0];
        if (s[1] === 1 && /ok|ready|complete/.test(s[0])) d.className = 'ok';
        if (s[1] === 2) d.className = 'wn';
        if (i === S.length - 1) d.className = 'caret';
        o.appendChild(d);
        pb.style.width = `${((i + 1) / S.length) * 100}%`;
      }

      function start(fast: boolean) {
        tm.forEach(clearTimeout);
        tm = [];
        if (o) o.textContent = '';
        if (pb) pb.style.width = '0';
        if (run) run.textContent = 'Replay';
        S.forEach((s, i) =>
          tm.push(
            setTimeout(() => {
              add(s, i);
              if (i === S.length - 1 && lv) {
                lv.textContent = 'Simulation finished. Three passed, one sample warning.';
              }
            }, fast || RM ? 0 : i * 600)
          )
        );
      }

      run.onclick = () => start(false);
      sk.onclick = () => start(true);

      const termObserver = new IntersectionObserver(
        (entries, ob) => {
          if (entries[0].isIntersecting) {
            start(false);
            ob.disconnect();
          }
        },
        { threshold: 0.4 }
      );
      termObserver.observe(o);
    })();

    // Scroll-driven File Scanner (#scan)
    (function initFileScanner() {
      const sec = document.getElementById('scan');
      const fl = document.getElementById('files');
      const bm = document.getElementById('sbeam');
      const rg = document.getElementById('rg');
      const cf = document.getElementById('cf');
      const cs = document.getElementById('cs');
      const vd = document.getElementById('verdict');
      const B = [document.getElementById('b1'), document.getElementById('b2'), document.getElementById('b3')];
      const pl = document.getElementById('play');
      const why = document.getElementById('why');
      const stp = [...document.querySelectorAll('.stp')];

      if (!sec || !fl || !bm || !rg || !cf || !cs || !vd || !why) return;

      const D: [string, string, string][] = [
        ['Login form', 'clean', 'This form takes a password and handles it safely, so it looks clean.'],
        ['Database settings', 'issue', 'A password was left in plain text in this settings file. This is a sample issue.'],
        ['Payment handler', 'review', 'It handles money and a few checks are missing, so a person should review it.'],
        ['File upload', 'issue', 'Users can send any file type here. This is a sample issue.'],
        ['Session manager', 'clean', 'Sign in sessions expire properly, so it looks clean.'],
        ['Dependency list', 'review', 'One outside package looks old, so it needs review.'],
        ['Search page', 'clean', 'Typed text is cleaned before use, so it looks clean.'],
        ['Admin panel', 'review', 'Access rules need a second look, so it needs review.'],
      ];

      const ST = ['Reading file', 'Checking inputs', 'Looking for secrets', 'Rating risk'];
      const SD = [
        'Opening the file and working out what it does.',
        'Seeing how it handles what users type or send.',
        'Searching for passwords or keys left in plain sight.',
        '',
      ];
      const W: Record<string, string> = {
        wait: 'Waiting',
        active: 'Scanning',
        clean: 'Looks clean',
        review: 'Needs review',
        issue: 'Sample issue',
      };

      const S = '<svg viewBox="0 0 20 20" fill="none" stroke-width="1.8" ';
      const IC: Record<string, string> = {
        wait: S + 'stroke="#6E829F"><circle cx="10" cy="10" r="7"/></svg>',
        active: S + 'class="spin" stroke="#00D9FF"><path d="M10 3a7 7 0 1 1-7 7"/></svg>',
        clean: S + 'stroke="#37D6A0"><circle cx="10" cy="10" r="7.5"/><path d="m6.5 10 2.5 2.5 4.5-5"/></svg>',
        review: S + 'stroke="#FFBD66"><path d="M10 3 18 17H2z"/><path d="M10 8v4M10 14.5v.5"/></svg>',
        issue: S + 'stroke="#FF526B"><rect x="3" y="3" width="14" height="14" rx="2"/><path d="m7 7 6 6M13 7l-6 6"/></svg>',
      };

      fl.querySelectorAll('.fr').forEach((el) => el.remove());
      const rows = D.map((d) => {
        const r: any = document.createElement('div');
        r.className = 'fr wait';
        r.setAttribute('role', 'listitem');
        const i = document.createElement('span');
        const n = document.createElement('span');
        const v = document.createElement('span');
        n.className = 'fn';
        n.textContent = d[0];
        v.className = 'fv';
        r.append(i, n, v);
        fl.appendChild(r);
        r._s = '';
        r._i = i;
        r._v = v;
        return r;
      });

      function scanExtra(p: number, done: boolean, cur: number, sub: number) {
        const si = Math.min(3, Math.floor(sub * 4));
        const d = D[cur];
        stp.forEach((e, idx) => {
          e.className = 'stp' + (done || (p > 0 && idx < si) ? ' dn' : p > 0 && idx === si ? ' on' : '');
        });
        if (why) {
          why.textContent =
            p <= 0
              ? 'Keep scrolling down. Each file is checked one at a time, and you will see why it passes or needs attention.'
              : done
              ? 'Finished. Every file now has a result you can read: looks clean, needs review, or sample issue.'
              : si < 3
              ? SD[si]
              : d[0] + '. ' + d[2];
        }
      }

      function setRow(r: any, s: string) {
        if (r._s === s) return;
        r._s = s;
        r.className = 'fr ' + s;
        r._i.innerHTML = IC[s];
        r._v.textContent = W[s];
      }

      function u() {
        if (!sec || !fl || !bm || !rg || !cf || !cs || !vd) return;
        const rc = sec.getBoundingClientRect();
        const tot = sec.offsetHeight - window.innerHeight;
        const p = Math.min(1, Math.max(0, -rc.top / tot));
        const f = p * D.length;
        const cur = Math.min(D.length - 1, Math.floor(f));
        const sub = f - cur;
        const done = p >= 0.995;

        const c = [0, 0, 0];
        rows.forEach((r, i) => {
          const fin = done || i < cur;
          setRow(r, fin ? D[i][1] : i === cur && p > 0 ? 'active' : 'wait');
          if (fin) {
            const idx = ['clean', 'review', 'issue'].indexOf(D[i][1]);
            if (idx >= 0) c[idx]++;
          }
        });

        const rr = rows[cur];
        if (rr) {
          const y = done ? fl.clientHeight : rr.offsetTop + rr.offsetHeight * (0.12 + 0.76 * sub);
          bm.style.transform = `translateY(${y}px)`;
          bm.style.opacity = p > 0 && !done ? '1' : '0';
        }

        rg.style.strokeDashoffset = `${327 * (1 - p)}`;
        B.forEach((b, i) => {
          if (b) b.style.width = `${(c[i] / D.length) * 100}%`;
        });

        cf.textContent = p <= 0 ? 'Waiting' : done ? 'Analysis complete' : D[cur][0];
        cs.textContent = p <= 0 ? 'Scroll to begin' : done ? 'All sample files reviewed' : ST[Math.min(3, Math.floor(sub * 4))];
        scanExtra(p, done, cur, sub);
        vd.textContent = done
          ? 'Sample report ready. Some files looked clean, some need review and some show sample issues. These results are made up for this demo.'
          : '';
      }

      window.addEventListener('scroll', u, { passive: true });
      window.addEventListener('resize', u);
      u();

      // Play the scan for me auto-scroll
      if (pl) {
        let raf = 0;
        function stop() {
          cancelAnimationFrame(raf);
          raf = 0;
          if (pl) pl.textContent = 'Play the scan for me';
          document.documentElement.style.scrollBehavior = '';
        }
        ['wheel', 'touchstart', 'keydown'].forEach((ev) =>
          window.addEventListener(ev, () => {
            if (raf) stop();
          }, { passive: true })
        );

        pl.onclick = () => {
          if (raf) {
            stop();
            return;
          }
          const y0 = sec.getBoundingClientRect().top + window.scrollY;
          const tot = sec.offsetHeight - window.innerHeight;
          let t0 = 0;
          pl.textContent = 'Stop the scan';
          document.documentElement.style.scrollBehavior = 'auto';
          function s(t: number) {
            if (!t0) t0 = t;
            const k = Math.min(1, (t - t0) / 44000);
            window.scrollTo(0, y0 + tot * k);
            if (k < 1 && raf) raf = requestAnimationFrame(s);
            else stop();
          }
          window.scrollTo(0, y0);
          raf = requestAnimationFrame(s);
        };
      }
    })();

    // Rail + Journey + Gauge
    (function initRailAndGauge() {
      const pipe = document.getElementById('pipe');
      const pl = document.getElementById('pl');
      const ri = document.getElementById('ri');
      const rb = document.getElementById('rb');
      if (!pipe || !pl || !ri || !rb) return;

      const st = [...pipe.querySelectorAll('.st')];
      const ids = ['top', 'features', 'terminal', 'learning', 'login'];
      const secs = ids.map((id) => document.getElementById(id));
      const gl = [...document.querySelectorAll('#gauge a')];
      const nl = [...document.querySelectorAll('nav a.l')];

      function u() {
        if (!pipe || !pl || !ri || !rb) return;
        const dh = document.documentElement.scrollHeight - window.innerHeight;
        const pr = dh > 0 ? window.scrollY / dh : 0;
        ri.style.height = `${pr * 100}%`;
        rb.style.top = `${pr * 100}%`;

        const b = pipe.getBoundingClientRect();
        const p = Math.min(1, Math.max(0, (window.innerHeight * 0.75 - b.top) / (b.height + window.innerHeight * 0.2)));
        if (window.innerWidth <= 820) {
          pl.style.setProperty('--h', `${p * 100}%`);
          pl.style.width = '100%';
        } else {
          pl.style.width = `${p * 100}%`;
        }

        st.forEach((s, i) => s.classList.toggle('on', p > (i + 0.2) / 3));

        let cur = 0;
        secs.forEach((s, i) => {
          if (s && s.getBoundingClientRect().top < window.innerHeight * 0.4) cur = i;
        });
        gl.forEach((a, i) => a.classList.toggle('on', i === cur));
        nl.forEach((a) => a.classList.toggle('on', a.getAttribute('href') === '#' + ids[cur]));
      }

      window.addEventListener('scroll', u, { passive: true });
      window.addEventListener('resize', u);
      u();
    })();

    // Airlock focus reacting canvas (#lc)
    let lcRaf: number;
    (function initAirlockCanvas() {
      const c = document.getElementById('lc') as HTMLCanvasElement;
      if (!c) return;
      const x = c.getContext('2d');
      if (!x) return;

      let W: number, H: number, N: any[] = [], boost = 0, tgt = 0, vis = true, pul = 0;

      function rs() {
        if (!c) return;
        W = c.width = c.clientWidth;
        H = c.height = c.clientHeight;
        N = [...Array(16)].map(() => ({
          x: Math.random() * W,
          y: Math.random() * H * 0.7,
          vx: (Math.random() - 0.5) * 0.4,
          vy: (Math.random() - 0.5) * 0.4,
        }));
      }
      rs();
      window.addEventListener('resize', rs);

      const fInputs = document.querySelectorAll('#f input');
      fInputs.forEach((i) => {
        i.addEventListener('focus', () => (tgt = 1));
        i.addEventListener('blur', () => (tgt = 0));
        i.addEventListener('input', () => (pul = 1));
      });

      let lt = 0;
      function f(ts: number) {
        if (!vis || !x) return;
        if (!RM && ts && ts - lt < 30) {
          lcRaf = requestAnimationFrame(f);
          return;
        }
        lt = ts || 0;
        x.clearRect(0, 0, W, H);
        boost += (tgt - boost) * 0.06;
        pul *= 0.97;
        const t = Date.now() / 1000;

        N.forEach((n) => {
          n.x += n.vx * (1 + boost * 2);
          n.y += n.vy * (1 + boost * 2);
          if (n.x < 0 || n.x > W) n.vx *= -1;
          if (n.y < 0 || n.y > H * 0.75) n.vy *= -1;
        });

        for (let i = 0; i < N.length; i++) {
          for (let j = i + 1; j < N.length; j++) {
            const a = N[i], b = N[j], d = Math.hypot(a.x - b.x, a.y - b.y);
            if (d < 150 + boost * 70) {
              x.strokeStyle = `rgba(0,217,255,${(1 - d / (150 + boost * 70)) * (0.25 + boost * 0.55 + pul * 0.3)})`;
              x.beginPath();
              x.moveTo(a.x, a.y);
              x.lineTo(b.x, b.y);
              x.stroke();
              if (boost > 0.3) {
                const u = (t * 0.8 + i * 0.13) % 1;
                x.fillStyle = '#fff';
                x.fillRect(a.x + (b.x - a.x) * u, a.y + (b.y - a.y) * u, 2.4, 2.4);
              }
            }
          }
        }

        N.forEach((n) => {
          x.fillStyle = `rgba(0,217,255,${0.6 + boost * 0.4})`;
          x.beginPath();
          x.arc(n.x, n.y, 2 + boost * 1.5, 0, 7);
          x.fill();
        });

        if (!RM) lcRaf = requestAnimationFrame(f);
      }
      f(0);
    })();

    return () => {
      clearTimeout(bootTimer);
      clearTimeout(revealTimer);
      clearTimeout(heroTypingTimeout);
      cancelAnimationFrame(bgRaf);
      cancelAnimationFrame(globeRaf);
      cancelAnimationFrame(lcRaf);
      window.removeEventListener('pointermove', onPointerMove);
    };
  }, []);

  return (
    <div ref={containerRef} className="zylorun-landing-root">
      {/* Inline styles for 100% faithful styling of the exact design preview */}
      <style>{`
        @property --a{syntax:'<angle>';initial-value:0deg;inherits:false}
        .zylorun-landing-root {
          --bg:#030712;--bg2:#07111F;--el:#0B1728;--glass:rgba(10,25,45,.78);--bd:rgba(67,150,255,.22);
          --blue:#087CFF;--cy:#00D9FF;--vi:#795BFF;--tx:#F2F7FF;--tx2:#9CB0CA;--ok:#37D6A0;--warn:#FFBD66;
          --ease:cubic-bezier(.22,1,.36,1);color-scheme:dark;box-sizing:border-box;
          background:var(--bg);color:var(--tx);font:16px/1.6 Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
          overflow-x:hidden;min-height:100vh;position:relative;
        }
        .zylorun-landing-root *{box-sizing:border-box}
        .zylorun-landing-root h1,.zylorun-landing-root h2,.zylorun-landing-root h3{font-family:"Space Grotesk",Inter,system-ui,sans-serif;line-height:1.05;margin:0;letter-spacing:-.02em}
        .zylorun-landing-root .mono{font-family:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace}
        .zylorun-landing-root a{color:inherit}:focus-visible{outline:2px solid var(--cy);outline-offset:3px;border-radius:6px}
        .skip{position:absolute;left:-999px}.skip:focus{left:12px;top:12px;background:var(--cy);color:#001;padding:8px 12px;z-index:99}
        #bg{position:fixed;inset:0;z-index:0;pointer-events:none}
        main,header,footer{position:relative;z-index:2}
        #boot{position:fixed;inset:0;z-index:100;background:var(--bg);display:grid;place-items:center;transition:opacity .6s,visibility .6s;cursor:pointer}
        #boot.out{opacity:0;visibility:hidden}
        #boot .b{width:min(340px,80vw);text-align:center;font-size:13px;color:var(--cy)}
        #boot .bar{height:2px;background:rgba(67,150,255,.2);margin:16px 0 10px;overflow:hidden}#boot .bar i{display:block;height:100%;width:0;background:var(--cy);box-shadow:0 0 14px var(--cy);animation:bl 1.2s var(--ease) forwards}
        @keyframes bl{to{width:100%}}
        #boot svg{animation:bp 1.2s ease-out}@keyframes bp{from{transform:scale(.4);opacity:0;filter:blur(8px)}to{transform:none;opacity:1;filter:none}}
        .rail{position:fixed;left:14px;top:0;bottom:0;width:2px;background:rgba(67,150,255,.12);z-index:3}
        .rail i{position:absolute;left:0;top:0;width:100%;height:0;background:linear-gradient(var(--blue),var(--cy))}
        .rail b{position:absolute;left:-5px;width:12px;height:12px;border-radius:50%;background:var(--cy);box-shadow:0 0 18px 4px var(--cy),0 0 40px var(--blue);top:0;transform:translateY(-6px)}
        @media(max-width:1000px){.rail{display:none}}
        header{position:fixed;inset:0 0 auto 0;z-index:20;padding-top:env(safe-area-inset-top,0px);background:rgba(3,7,18,.94);border-bottom:1px solid var(--bd)}
        nav{max-width:1200px;margin:auto;display:flex;align-items:center;gap:22px;padding:12px 20px}
        .logo{display:flex;gap:10px;align-items:center;font:700 19px "Space Grotesk",sans-serif;text-decoration:none;margin-right:auto}
        nav a.l{position:relative;color:var(--tx2);text-decoration:none;font-size:15px;padding:6px 2px;transition:color .2s}
        nav a.l::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:var(--cy);transform:scaleX(0);transition:transform .4s var(--ease);box-shadow:0 0 8px var(--cy)}
        nav a.l:hover,nav a.l.on{color:var(--tx)}nav a.l:hover::after,nav a.l.on::after{transform:scaleX(1)}
        .btn{position:relative;display:inline-flex;align-items:center;gap:8px;padding:11px 20px;border-radius:10px;font:600 15px Inter,sans-serif;text-decoration:none;border:1px solid var(--bd);background:transparent;color:var(--tx);cursor:pointer;min-height:44px;overflow:hidden;transition:box-shadow .25s,background .25s}
        .btn.p{background:var(--blue);border-color:var(--blue);box-shadow:0 0 18px rgba(8,124,255,.45)}
        @keyframes glow{50%{box-shadow:0 0 26px rgba(8,124,255,.6)}}
        .btn::after{content:"";position:absolute;top:0;bottom:0;width:40%;left:-60%;background:linear-gradient(100deg,transparent,rgba(255,255,255,.35),transparent);transform:skewX(-20deg)}
        .btn:hover::after{left:130%;transition:left .7s var(--ease)}
        .btn:not(.p):hover{background:rgba(8,124,255,.14);border-color:var(--cy)}
        @media(max-width:820px){nav a.l{display:none}nav{gap:10px}nav .btn{padding:8px 14px;white-space:nowrap;min-height:40px}}
        #gauge{position:fixed;right:18px;top:50%;transform:translateY(-50%);z-index:15;display:flex;flex-direction:column;gap:14px;font-size:11px}
        #gauge a{color:var(--tx2);text-decoration:none;display:flex;align-items:center;gap:8px;justify-content:flex-end;opacity:.55;transition:all .4s}
        #gauge a i{width:8px;height:8px;border-radius:50%;border:1px solid var(--cy);display:block;transition:all .4s}
        #gauge a.on{opacity:1;color:var(--cy);transform:translateX(-6px)}#gauge a.on i{background:var(--cy);box-shadow:0 0 12px var(--cy);transform:scale(1.5)}
        @media(max-width:1100px){#gauge{display:none}}
        section{position:relative;padding:110px 20px;max-width:1200px;margin:auto}
        .sec::before{content:"";position:absolute;left:0;top:0;width:100%;height:2px;background:linear-gradient(90deg,transparent,var(--cy),transparent);opacity:0;pointer-events:none;box-shadow:0 0 16px var(--cy)}
        .sec.in::before{animation:wipe 1.3s var(--ease)}@keyframes wipe{0%{transform:translateX(-100%);opacity:1}100%{transform:translateX(100%);opacity:0}}
        .hero{min-height:100svh;display:grid;grid-template-columns:1.05fr 1fr;align-items:center;gap:20px;padding-top:120px;overflow:visible}
        .xray{position:absolute;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(rgba(0,217,255,.35) 1px,transparent 1px),linear-gradient(90deg,rgba(0,217,255,.35) 1px,transparent 1px);background-size:44px 44px;-webkit-mask-image:radial-gradient(circle 170px at var(--mx,-999px) var(--my,-999px),#000,transparent);mask-image:radial-gradient(circle 170px at var(--mx,-999px) var(--my,-999px),#000,transparent)}
        .xray span{position:absolute;font-size:10px;color:var(--cy);opacity:.9}
        .hero>*:not(.xray){position:relative;z-index:1}
        .hero h1{font-size:clamp(38px,5.2vw,74px);font-weight:700;min-height:2.1em}
        .hero p{color:var(--tx2);max-width:52ch;font-size:18px;margin:22px 0 30px}
        .cta{display:flex;gap:12px;flex-wrap:wrap}
        .stage{position:relative;aspect-ratio:1;width:100%;max-width:640px;justify-self:center;will-change:transform}
        .stage canvas{position:absolute;inset:0;width:100%;height:100%}
        .shield{position:absolute;left:50%;top:50%;width:28%;transform:translate(-50%,-50%);filter:drop-shadow(0 0 24px rgba(0,217,255,.7));animation:fl 6s ease-in-out infinite}
        @keyframes fl{50%{transform:translate(-50%,-56%)}}
        .pulse{position:absolute;left:50%;top:50%;width:30%;aspect-ratio:1;border:1px solid var(--cy);border-radius:50%;transform:translate(-50%,-50%) scale(.5);opacity:0;animation:pu 4s ease-out infinite}
        .pulse:nth-of-type(2){animation-delay:1.3s}.pulse:nth-of-type(3){animation-delay:2.6s}
        @keyframes pu{0%{opacity:.8;transform:translate(-50%,-50%) scale(.6)}100%{opacity:0;transform:translate(-50%,-50%) scale(3.2)}}
        .ring{position:absolute;left:50%;top:50%;border:1px dashed rgba(0,217,255,.5);border-radius:50%;animation:spin 24s linear infinite}
        .r1{width:42%;height:42%;margin:-21% 0 0 -21%}.r2{width:52%;height:52%;margin:-26% 0 0 -26%;animation-duration:36s;animation-direction:reverse;border-color:rgba(121,91,255,.5)}
        @keyframes spin{to{transform:rotate(360deg)}}
        .panel{position:absolute;background:var(--glass);border:1px solid var(--bd);border-radius:10px;padding:10px 12px;font-size:12px;background:rgba(10,25,45,.92);animation:bob 7s ease-in-out infinite;min-width:170px}
        .panel b{color:var(--cy);font-weight:500}.p1{left:-2%;top:6%}.p2{right:-2%;bottom:10%;animation-delay:-3s}
        @keyframes bob{50%{translate:0 -10px}}
        .caret::after{content:"";display:inline-block;width:.55em;height:1em;vertical-align:-.15em;background:var(--cy);animation:cb 1s steps(1) infinite}@keyframes cb{50%{opacity:0}}
        .tag{display:inline-block;font-size:11px;border:1px solid var(--warn);color:var(--warn);border-radius:99px;padding:1px 8px;margin-bottom:4px}
        @media(max-width:820px){.hero{grid-template-columns:1fr;padding-top:100px}.stage{max-width:420px}.p1{left:0}.p2{right:0}}
        .mq{overflow:hidden;border-block:1px solid var(--bd);background:rgba(7,17,31,.6);padding:14px 0;white-space:nowrap}
        .mq div{display:inline-block;animation:mq 30s linear infinite;color:var(--tx2);font-size:14px}.mq span{margin:0 26px}.mq span::before{content:"";display:inline-block;width:7px;height:7px;background:var(--cy);transform:rotate(45deg);margin-right:26px}
        @keyframes mq{to{transform:translateX(-50%)}}
        h2{font-size:clamp(30px,4.4vw,52px);margin-bottom:14px}.lead{color:var(--tx2);max-width:60ch}
        .map{display:grid;grid-template-columns:1.1fr 1fr;gap:30px;margin-top:40px;align-items:center}
        .graph{position:relative;aspect-ratio:1;max-width:520px;width:100%}
        .graph svg.ln{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
        .node{position:absolute;transform:translate(-50%,-50%);background:var(--el);border:1px solid var(--bd);color:var(--tx);border-radius:99px;padding:8px 14px;font:500 13px Inter,sans-serif;cursor:pointer;white-space:nowrap;transition:all .3s var(--ease);min-height:40px;animation:nb 5s ease-in-out infinite}
        @keyframes nb{50%{translate:0 -6px}}
        .node:hover,.node[aria-pressed=true]{border-color:var(--cy);box-shadow:0 0 26px rgba(0,217,255,.45);transform:translate(-50%,-50%) scale(1.1);background:#0f2440}
        .core{position:absolute;left:50%;top:50%;width:70px;transform:translate(-50%,-50%);filter:drop-shadow(0 0 14px var(--cy));animation:fl 5s ease-in-out infinite}
        .detail{background:var(--glass);border:1px solid var(--bd);border-radius:14px;padding:26px;min-height:230px}
        .detail h3{font-size:26px;margin:10px 0 8px}.detail p{color:var(--tx2)}
        .detail.sw{animation:sw .5s var(--ease)}@keyframes sw{from{opacity:0;transform:translateX(24px) rotateY(-12deg)}}
        .chip{display:inline-flex;font-size:12px;border-radius:99px;padding:2px 10px;border:1px solid var(--warn);color:var(--warn)}
        @media(max-width:820px){.map{grid-template-columns:1fr}}
        @media(max-width:560px){.graph{width:calc(100% - 70px);margin:0 auto}.node{font-size:12px;padding:6px 10px}}
        .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:50px;perspective:900px}
        .card{--px:50%;--py:50%;position:relative;background:var(--el);border-radius:14px;padding:24px 20px;min-height:170px;transition:transform .25s var(--ease);transform-style:preserve-3d;overflow:hidden}
        .card::before{content:"";position:absolute;inset:0;border-radius:14px;padding:1.5px;background:conic-gradient(from var(--a),transparent 55%,var(--cy),var(--vi),transparent);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude}
        .card:hover::before{animation:rot 3s linear infinite}@keyframes rot{to{--a:360deg}}
        .card::after{content:"";position:absolute;inset:0;background:radial-gradient(220px circle at var(--px) var(--py),rgba(0,217,255,.18),transparent 70%);opacity:0;transition:opacity .3s}
        .card:hover::after{opacity:1}.card h3{font-size:20px;margin:12px 0 6px;transform:translateZ(30px)}.card p{color:var(--tx2);font-size:14px;margin:0 0 10px}
        .card svg{transition:transform .5s var(--ease)}.card:hover svg{transform:rotate(12deg) scale(1.2)}
        @media(max-width:900px){.cards{grid-template-columns:1fr 1fr}}@media(max-width:520px){.cards{grid-template-columns:1fr}}
        .term{margin-top:34px;background:#050c18;border:1px solid var(--bd);border-radius:12px;overflow:hidden;box-shadow:0 20px 60px rgba(0,100,255,.15)}
        .th{display:flex;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px solid var(--bd);font-size:12px;color:var(--tx2)}.th .tag{margin:0 0 0 auto}
        pre{margin:0;padding:18px;min-height:270px;font-size:13.5px;line-height:1.7;overflow-x:auto;white-space:pre-wrap;color:#bcd6ff;position:relative}
        .beam{position:absolute;left:0;right:0;height:60px;background:linear-gradient(transparent,rgba(0,217,255,.14),transparent);animation:bm 3.5s linear infinite;pointer-events:none}
        @keyframes bm{from{top:-60px}to{top:100%}}
        .bar{height:3px;background:rgba(67,150,255,.15)}.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--blue),var(--cy));box-shadow:0 0 10px var(--cy);transition:width .4s}
        .tc{display:flex;gap:10px;padding:12px 14px;border-top:1px solid var(--bd);flex-wrap:wrap;align-items:center}.tc small{color:var(--tx2);margin-left:auto}
        .ok{color:var(--ok)}.wn{color:var(--warn)}pre div{animation:ln .35s var(--ease)}@keyframes ln{from{opacity:0;transform:translateX(-12px)}}
        .scan{height:800vh;padding:0 20px}
        .scanin{position:sticky;top:0;height:100vh;display:flex;flex-direction:column;justify-content:center;gap:22px;padding-top:70px;padding-bottom:84px}
        .scgrid{display:grid;grid-template-columns:1.1fr 1fr;gap:24px;align-items:stretch}
        .files{position:relative;background:#050c18;border:1px solid var(--bd);border-radius:12px;padding:8px;overflow:hidden}
        .fr{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:8px;transition:background .3s,opacity .3s;font-size:15px}
        .fr .fn{flex:1}.fr .fv{font-size:13px;color:var(--tx2)}.fr svg{width:20px;height:20px;flex:none}
        .fr.wait{opacity:.5}.fr.active{background:rgba(0,217,255,.12);box-shadow:inset 3px 0 var(--cy);opacity:1}
        .fr.clean .fv{color:var(--ok)}.fr.review .fv{color:var(--warn)}.fr.issue .fv{color:#ff8a9a}
        .spin{animation:spn 1s linear infinite}@keyframes spn{to{transform:rotate(360deg)}}
        .sbeam{position:absolute;left:0;right:0;top:0;height:46px;margin-top:-23px;background:linear-gradient(transparent,rgba(0,217,255,.28),transparent);border-block:1px solid rgba(0,217,255,.6);pointer-events:none;will-change:transform}
        .ana{background:var(--glass);border:1px solid var(--bd);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
        .anab{display:flex;gap:18px;align-items:center;padding:20px}
        .ringsv{width:92px;height:92px;transform:rotate(-90deg);flex:none}
        .rt{fill:none;stroke:rgba(67,150,255,.2);stroke-width:8}.rf{fill:none;stroke:var(--cy);stroke-width:8;stroke-linecap:round;stroke-dasharray:327;stroke-dashoffset:327;filter:drop-shadow(0 0 6px var(--cy))}
        .cs{color:var(--tx2)}#cf{font-size:17px;color:var(--tx)}
        .meters{padding:0 20px 14px;display:grid;gap:10px}.m{display:grid;grid-template-columns:130px 1fr;gap:10px;align-items:center;font-size:14px;color:var(--tx2)}
        .mb{height:8px;background:rgba(67,150,255,.15);border-radius:99px;overflow:hidden}.mb i{display:block;height:100%;width:0;border-radius:99px;transition:width .5s var(--ease)}
        .verd{padding:6px 20px 20px;color:var(--tx2);min-height:4.6em}
        @media(max-width:820px){.scgrid{grid-template-columns:1fr}.scanin .lead,.meters{display:none}.fr{padding:7px 10px;font-size:14px}.anab{padding:12px}.ringsv{width:64px;height:64px}.scanin{gap:12px}.scan h2{font-size:26px}.verd{min-height:3.4em}}
        #bg{opacity:.45}.lite #bg,.lite .xray{display:none}.lite .pulse,.lite .beam,.lite .ring,.lite .btn::after{animation:none}
        #cap{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:30;width:max-content;max-width:min(680px,90vw);background:rgba(5,12,24,.94);border:1px solid var(--cy);border-radius:14px;padding:10px 18px;font-size:16px;color:var(--tx);box-shadow:0 0 30px rgba(0,217,255,.2);text-align:center;transition:opacity .4s}
        #cap small{display:block;color:var(--cy);font-size:13px;margin-bottom:2px}
        .fr{font-size:16px}.fr .fv{font-size:14px}.anab{padding:14px 20px}.verd{min-height:3.2em;padding:6px 20px 14px}
        .steps{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;padding:0 20px 12px}
        .stp{font-size:13px;color:var(--tx2);border-top:3px solid rgba(67,150,255,.25);padding-top:6px;transition:color .12s,border-color .12s}
        .stp.on{color:var(--tx);border-color:var(--cy)}.stp.dn{color:var(--ok);border-color:var(--ok)}
        .why{margin:0 20px 12px;padding:10px 14px;border-left:3px solid var(--cy);background:rgba(0,217,255,.08);border-radius:0 8px 8px 0;font-size:15px;color:var(--tx);min-height:4.2em}
        .sh2{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}.sh2 h2{margin:0}.sh2 .cta{gap:10px}.sh2 .btn{padding:8px 16px;min-height:40px}
        @media(max-height:900px){.scanin .lead{display:none}}
        @media(max-width:820px){.sh2 .btn:not(.p){display:none}.sh2 .btn{padding:6px 12px;min-height:36px;font-size:14px}}
        @media(max-width:820px){#cap{display:none}.steps{display:none}.why{font-size:14px;min-height:3.6em;margin:0 12px 8px;padding:8px 10px}}
        .pipe{position:relative;display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:50px}
        .pipe .line{position:absolute;left:0;right:0;top:22px;height:2px;background:rgba(67,150,255,.2)}
        .pipe .line i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--blue),var(--cy));box-shadow:0 0 14px var(--cy);position:relative}
        .pipe .line i::after{content:"";position:absolute;right:-5px;top:-4px;width:10px;height:10px;border-radius:50%;background:#fff;box-shadow:0 0 16px 4px var(--cy)}
        .st{position:relative;padding-top:56px;opacity:.65;transform:translateY(12px);transition:all .8s var(--ease)}.st.on{opacity:1;transform:none}
        .st .dot{position:absolute;top:12px;left:0;width:22px;height:22px;border-radius:50%;background:var(--bg);border:2px solid var(--bd);transition:all .5s}
        .st.on .dot{border-color:var(--cy);background:var(--cy);box-shadow:0 0 22px var(--cy)}@keyframes dp{50%{box-shadow:0 0 0 12px rgba(0,217,255,0)}}
        .st h3{font-size:26px;margin-bottom:6px}.st p{color:var(--tx2)}
        @media(max-width:820px){.pipe{grid-template-columns:1fr}.pipe .line{left:10px;right:auto;width:2px;height:100%;top:0}.pipe .line i{width:100%!important;height:var(--h,0%)}.st{padding:0 0 28px 42px}.st .dot{top:4px}}
        .auth{display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--bd);border-radius:18px;overflow:hidden;margin-top:38px;background:var(--bg2)}
        .aL{padding:40px;min-height:430px;position:relative;background:radial-gradient(120% 90% at 20% 100%,rgba(8,124,255,.35),transparent 60%),linear-gradient(180deg,#050d1c,#07111F);overflow:hidden}
        .aL canvas{position:absolute;inset:0;width:100%;height:100%}.aL>*:not(canvas){position:relative;z-index:1}
        .aL h3{font-size:clamp(26px,3vw,38px);margin-top:70px}.aL p{color:var(--tx2);max-width:34ch}
        .ridge{position:absolute!important;left:0;right:0;bottom:0;height:42%;opacity:.85;z-index:0!important}
        .aR{padding:40px;display:flex;flex-direction:column;gap:14px;justify-content:center}
        label{font-size:14px;color:var(--tx2);display:block;margin-bottom:4px}
        input{width:100%;background:var(--el);border:1px solid var(--bd);border-radius:10px;padding:12px 14px;color:var(--tx);font:16px Inter,sans-serif;min-height:46px;transition:all .3s}
        input:focus{border-color:var(--cy);outline:none;box-shadow:0 0 0 3px rgba(0,217,255,.22),0 0 24px rgba(0,217,255,.2)}
        .err{color:#ff8a9a;font-size:14px;min-height:20px}.sh{animation:nudge .35s}@keyframes nudge{30%{transform:translateX(-5px)}70%{transform:translateX(5px)}}
        .note{font-size:13px;color:var(--tx2);border-top:1px dashed var(--bd);padding-top:12px;margin-top:6px}
        @media(max-width:820px){.auth{grid-template-columns:1fr}.aL{min-height:270px}.aL h3{margin-top:30px}.aL,.aR{padding:26px}}
        .final{text-align:center;padding:140px 20px}.final h2{font-size:clamp(34px,5.5vw,68px)}.final .cta{justify-content:center;margin-top:28px}
        .fs{position:relative;width:120px;height:140px;margin:0 auto 24px}.fs svg{position:absolute;inset:0;width:100%;height:100%;filter:drop-shadow(0 0 22px var(--cy));animation:fl2 5s ease-in-out infinite}
        @keyframes fl2{50%{transform:translateY(-8px)}}.fs .pulse{width:100%;top:55%}
        footer{border-top:1px solid var(--bd);padding:26px 20px;text-align:center;color:var(--tx2);font-size:14px;background:var(--bg)}
        .rv{opacity:1}.js .rv{opacity:0;transform:translateY(30px);transition:opacity .8s var(--ease),transform .8s var(--ease)}.js .rv.in{opacity:1;transform:none}
        @media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}html{scroll-behavior:auto}.js .rv{opacity:1;transform:none;filter:none}#boot{display:none}.st{opacity:1;transform:none}}
      `}</style>

      {/* Boot loader screen */}
      <div id="boot" role="status" aria-label="Loading">
        <div className="b mono">
          <svg width="54" height="62" viewBox="0 0 26 30" aria-hidden="true">
            <path d="M13 1 24 5v9c0 7-5 12-11 15C7 26 2 21 2 14V5z" fill="#087CFF" stroke="#00D9FF" />
            <path d="M8 9h10L8 21h10" stroke="#fff" strokeWidth="2.6" fill="none" />
          </svg>
          <div className="bar">
            <i></i>
          </div>
          INITIALIZING SIGNAL ROOM
          <br />
          <small style={{ color: '#6E829F' }}>click to skip</small>
        </div>
      </div>

      {/* Background canvas */}
      <canvas id="bg" aria-hidden="true"></canvas>

      {/* Scroll rail */}
      <div className="rail" aria-hidden="true">
        <i id="ri"></i>
        <b id="rb"></b>
      </div>

      <a className="skip" href="#main">
        Skip to content
      </a>

      {/* Header */}
      <header>
        <nav aria-label="Main">
          <a className="logo" href="#top">
            <svg width="26" height="30" viewBox="0 0 26 30" aria-hidden="true">
              <path d="M13 1 24 5v9c0 7-5 12-11 15C7 26 2 21 2 14V5z" fill="#087CFF" stroke="#00D9FF" />
              <path d="M8 9h10L8 21h10" stroke="#fff" strokeWidth="2.6" fill="none" />
            </svg>
            ZyloRun
          </a>
          <a className="l on" href="#top">
            Home
          </a>
          <a className="l" href="#features">
            Features
          </a>
          <a className="l" href="#terminal">
            Tools
          </a>
          <a className="l" href="#learning">
            Learning
          </a>
          <button type="button" className="btn mag" onClick={() => navigate('/login')}>
            Login
          </button>
          <button type="button" className="btn p mag" onClick={() => navigate('/register')}>
            Get Started
          </button>
        </nav>
      </header>

      {/* Right HUD Gauge */}
      <div id="gauge" className="mono" aria-label="Page layers">
        <a href="#top" className="on">
          ORBIT<i></i>
        </a>
        <a href="#features">
          NETWORK<i></i>
        </a>
        <a href="#terminal">
          HOST<i></i>
        </a>
        <a href="#learning">
          PROCESS<i></i>
        </a>
        <a href="#login">
          AIRLOCK<i></i>
        </a>
      </div>

      <main id="main">
        {/* 1. Hero Section */}
        <section className="hero" id="top">
          <div className="xray mono" aria-hidden="true">
            <span style={{ left: '8%', top: '22%' }}>NODE ALPHA</span>
            <span style={{ left: '46%', top: '14%' }}>SECTOR FOUR</span>
            <span style={{ left: '30%', top: '70%' }}>SECURE LINK OK</span>
            <span style={{ left: '70%', top: '55%' }}>PACKET FLOW</span>
            <span style={{ left: '12%', top: '84%' }}>LATITUDE LONGITUDE</span>
          </div>
          <div>
            <h1 id="h1" aria-label="Sharpen Your Skills. Secure a Safer Tomorrow.">
              Sharpen Your Skills. Secure a Safer Tomorrow.
            </h1>
            <p>
              Learn cybersecurity by doing. Explore hands-on security labs, practice real-world scenarios, and build the
              skills to identify, understand, and respond to security threats.
            </p>
            <div className="cta">
              <a className="btn p mag" href="#learning">
                Start Learning
              </a>
              <a className="btn mag" href="#terminal">
                Explore Tools
              </a>
            </div>
          </div>
          <div className="stage" id="stage" aria-hidden="true">
            <canvas id="globe"></canvas>
            <div className="ring r1"></div>
            <div className="ring r2"></div>
            <i className="pulse"></i>
            <i className="pulse"></i>
            <i className="pulse"></i>
            <svg className="shield" viewBox="0 0 100 116">
              <defs>
                <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stopColor="#00D9FF" />
                  <stop offset="1" stopColor="#087CFF" />
                </linearGradient>
              </defs>
              <path
                d="M50 3 92 18v36c0 28-19 48-42 59C27 102 8 82 8 54V18z"
                fill="rgba(8,124,255,.28)"
                stroke="url(#g)"
                strokeWidth="3"
              />
              <path d="M50 3v110M8 36h84" stroke="rgba(0,217,255,.25)" />
              <path d="M33 40h34L33 80h34" stroke="#fff" strokeWidth="8" fill="none" strokeLinejoin="miter" />
            </svg>
            <div className="panel p1 mono">
              <span className="tag">SIMULATION</span>
              <div id="ht" className="caret" style={{ minHeight: '3.4em', whiteSpace: 'pre' }}></div>
            </div>
            <div className="panel p2 mono">
              <span className="tag">SAMPLE OUTPUT</span>
              <br />
              Example finding
              <br />
              <span className="wn">Medium risk</span>, not a real scan
            </div>
          </div>
        </section>

        {/* Ticker marquee */}
        <div className="mq mono" aria-hidden="true">
          <div>
            <span>RECONNAISSANCE</span>
            <span>ENUMERATION</span>
            <span>WEB APP SECURITY</span>
            <span>NETWORK ANALYSIS</span>
            <span>LOG MONITORING</span>
            <span>INCIDENT RESPONSE</span>
            <span>HARDENING</span>
            <span>REPORTING</span>
            <span>RECONNAISSANCE</span>
            <span>ENUMERATION</span>
            <span>WEB APP SECURITY</span>
            <span>NETWORK ANALYSIS</span>
            <span>LOG MONITORING</span>
            <span>INCIDENT RESPONSE</span>
            <span>HARDENING</span>
            <span>REPORTING</span>
          </div>
        </div>

        {/* 2. Features Section */}
        <section id="features" className="sec">
          <div className="rv">
            <h2 data-d>Every skill is a node on the map.</h2>
            <p className="lead">
              Pick a node to see what it covers. Each is marked as planned until it is connected to real content in your
              repository.
            </p>
          </div>
          <div className="map rv">
            <div className="graph" id="graph" role="group" aria-label="Feature map">
              <svg className="ln" id="lines" viewBox="0 0 100 100" preserveAspectRatio="none"></svg>
              <svg className="core" viewBox="0 0 100 116" aria-hidden="true">
                <path
                  d="M50 3 92 18v36c0 28-19 48-42 59C27 102 8 82 8 54V18z"
                  fill="rgba(8,124,255,.3)"
                  stroke="#00D9FF"
                  strokeWidth="3"
                />
              </svg>
            </div>
            <div className="detail" id="det" aria-live="polite">
              <span className="chip">Planned</span>
              <h3 id="dt"></h3>
              <p id="dd"></p>
              <a className="btn mag" style={{ marginTop: '14px' }} href="#terminal">
                See the simulation
              </a>
            </div>
          </div>
          <div className="cards">
            <div className="card" data-tilt>
              <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#00D9FF" strokeWidth="1.8">
                <path d="M4 17l6-6-6-6M12 19h8" />
              </svg>
              <h3>Guided labs</h3>
              <p>Step-by-step exercises in a contained space.</p>
              <span className="chip">Planned</span>
            </div>
            <div className="card" data-tilt>
              <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#00D9FF" strokeWidth="1.8">
                <circle cx="12" cy="12" r="9" />
                <path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" />
              </svg>
              <h3>Learning paths</h3>
              <p>Beginner to advanced, in a clear order.</p>
              <span className="chip">Planned</span>
            </div>
            <div className="card" data-tilt>
              <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#00D9FF" strokeWidth="1.8">
                <path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z" />
                <path d="m8.5 12 2.5 2.5 4.5-5" />
              </svg>
              <h3>Test runner</h3>
              <p>Run checks and read plain-language results.</p>
              <span className="chip">Planned</span>
            </div>
            <div className="card" data-tilt>
              <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#00D9FF" strokeWidth="1.8">
                <path d="M14 7l3-3 3 3-3 3M3 21l9-9M12 12l2 2" />
              </svg>
              <h3>Practical tools</h3>
              <p>Hands-on utilities for everyday security work.</p>
              <span className="chip">Planned</span>
            </div>
          </div>
        </section>

        {/* 3. Terminal Section */}
        <section id="terminal" className="sec">
          <div className="rv">
            <h2 data-d>Watch a harmless scan run.</h2>
            <p className="lead">
              A scripted demonstration. Nothing connects to a real system and nothing you type is executed.
            </p>
          </div>
          <div className="term rv">
            <div className="th mono">
              <span>zylorun lab scan demo</span>
              <span className="tag">SIMULATION</span>
            </div>
            <div className="bar">
              <i id="pb"></i>
            </div>
            <div style={{ position: 'relative' }}>
              <pre id="out" className="mono" role="log" aria-label="Simulated output"></pre>
              <div className="beam"></div>
            </div>
            <div className="tc">
              <button className="btn p mag" id="run" type="button">
                Run demo
              </button>
              <button className="btn" id="skip" type="button">
                Skip to end
              </button>
              <small>Predefined output with a reserved example target</small>
            </div>
          </div>
          <div id="live" className="skip" aria-live="polite"></div>
        </section>

        {/* 4. Scroll-driven File Scanner Section */}
        <section id="scan" className="sec scan">
          <div className="scanin">
            <div>
              <div className="sh2">
                <h2 data-d>Scroll to scan the files.</h2>
                <div className="cta">
                  <button className="btn p" id="play" type="button">
                    Play the scan for me
                  </button>
                  <a className="btn" href="#learning">
                    Skip scan
                  </a>
                </div>
              </div>
              <p className="lead">
                Keep scrolling and watch a sample project get scanned and analyzed file by file. This is a simulation
                and every result is made up for the demo.
              </p>
            </div>
            <div className="scgrid">
              <div className="files" id="files" role="list" aria-label="Sample files being scanned">
                <div className="sbeam" id="sbeam" aria-hidden="true"></div>
              </div>
              <div className="ana">
                <div className="th mono">
                  <span>analysis engine</span>
                  <span className="tag">SIMULATION</span>
                </div>
                <div className="anab">
                  <svg className="ringsv" viewBox="0 0 120 120" aria-hidden="true">
                    <circle cx="60" cy="60" r="52" className="rt" />
                    <circle id="rg" cx="60" cy="60" r="52" className="rf" />
                  </svg>
                  <div>
                    <div className="mono" id="cf">
                      Waiting
                    </div>
                    <div id="cs" className="cs">
                      Scroll to begin
                    </div>
                  </div>
                </div>
                <div className="steps">
                  <div className="stp">Read the file</div>
                  <div className="stp">Check inputs</div>
                  <div className="stp">Find secrets</div>
                  <div className="stp">Rate the risk</div>
                </div>
                <div className="why" id="why"></div>
                <div className="meters">
                  <div className="m">
                    <span>Looks clean</span>
                    <div className="mb">
                      <i id="b1" style={{ background: 'var(--ok)' }}></i>
                    </div>
                  </div>
                  <div className="m">
                    <span>Needs review</span>
                    <div className="mb">
                      <i id="b2" style={{ background: 'var(--warn)' }}></i>
                    </div>
                  </div>
                  <div className="m">
                    <span>Sample issue</span>
                    <div className="mb">
                      <i id="b3" style={{ background: '#FF526B' }}></i>
                    </div>
                  </div>
                </div>
                <div className="verd" id="verdict" aria-live="polite"></div>
              </div>
            </div>
          </div>
        </section>

        {/* 5. Learning Pipeline */}
        <section id="learning" className="sec">
          <div className="rv">
            <h2 data-d>Learn it. Break it safely. Do it better.</h2>
          </div>
          <div className="pipe" id="pipe">
            <div className="line">
              <i id="pl"></i>
            </div>
            <div className="st">
              <span className="dot"></span>
              <h3>Learn</h3>
              <p>Understand attack surfaces, defensive principles and the tools professionals use.</p>
            </div>
            <div className="st">
              <span className="dot"></span>
              <h3>Practice</h3>
              <p>Apply each idea in an authorized, controlled environment built for learning.</p>
            </div>
            <div className="st">
              <span className="dot"></span>
              <h3>Improve</h3>
              <p>Review results, close knowledge gaps and see your progress once you sign in.</p>
            </div>
          </div>
        </section>

        {/* 6. Airlock Login Section */}
        <section id="login" className="sec">
          <div className="rv">
            <h2 data-d>The quiet airlock.</h2>
            <p className="lead">
              Sign in to your ZyloRun workspace. Enter your credentials to access your autonomous security dashboard.
            </p>
          </div>
          <div className="auth rv">
            <div className="aL">
              <canvas id="lc" aria-hidden="true"></canvas>
              <svg className="ridge" viewBox="0 0 400 150" preserveAspectRatio="none" aria-hidden="true">
                <path d="M0 150V90l60-40 50 30 70-60 60 50 70-30 90 70v40z" fill="#061226" />
                <path d="M0 150v-40l80-30 60 25 90-50 80 40 90-20v75z" fill="#040b18" />
              </svg>
              <h3>
                Secure Access.
                <br />
                A Smarter Way to Learn.
              </h3>
              <p>Sign in to pick up where you left off.</p>
            </div>
            <form className="aR" id="f" onSubmit={handleAirlockSubmit}>
              <h3 style={{ fontSize: '28px' }}>Welcome back</h3>
              <div>
                <label htmlFor="em">Email address</label>
                <input
                  id="em"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@domain.com"
                />
              </div>
              <div>
                <label htmlFor="pw">Password</label>
                <input
                  id="pw"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
              {authError && (
                <div className="err" id="er" role="alert" style={{ color: '#ff8a9a', fontSize: '14px' }}>
                  {authError}
                </div>
              )}
              <button className="btn p" type="submit" style={{ justifyContent: 'center' }} disabled={isLoggingIn}>
                {isLoggingIn ? 'Authenticating...' : 'Sign in to ZyloRun'}
              </button>
              <p className="note">
                New to ZyloRun? Accounts entered here are instantly verified and securely authorized.
              </p>
            </form>
          </div>
        </section>

        {/* 7. Final Call to Action */}
        <section className="final sec">
          <div className="rv">
            <div className="fs" aria-hidden="true">
              <i className="pulse"></i>
              <i className="pulse"></i>
              <svg viewBox="0 0 100 116">
                <path
                  d="M50 3 92 18v36c0 28-19 48-42 59C27 102 8 82 8 54V18z"
                  fill="rgba(8,124,255,.3)"
                  stroke="#00D9FF"
                  strokeWidth="3"
                />
                <path d="M33 40h34L33 80h34" stroke="#fff" strokeWidth="8" fill="none" strokeLinejoin="miter" />
              </svg>
            </div>
            <h2 data-d>Your Security Journey Starts Here.</h2>
            <p className="lead" style={{ margin: '14px auto 0' }}>
              Learn. Practice. Test. Improve.
            </p>
            <div className="cta">
              <button type="button" className="btn p mag" onClick={() => navigate('/register')}>
                Get Started
              </button>
              <a className="btn mag" href="#learning">
                Explore Learning Resources
              </a>
            </div>
          </div>
        </section>
        <div style={{ height: '70px' }} aria-hidden="true" />
      </main>

      {/* Static / Fixed Highlighted Vovalyx Footer */}
      <footer
        onClick={() => window.open('https://www.vovalyx.in/', '_blank', 'noopener,noreferrer')}
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 999,
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          padding: '12px 28px',
          background: 'rgba(10, 14, 23, 0.92)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderTop: '1px solid rgba(0, 217, 255, 0.45)',
          boxShadow: '0 -4px 24px rgba(0, 217, 255, 0.2), 0 -1px 4px rgba(0, 0, 0, 0.8)',
          cursor: 'pointer',
          transition: 'all 0.25s ease'
        }}
        title="Click to visit Vovalyx (https://www.vovalyx.in/)"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '4px 10px',
              borderRadius: '8px',
              background: 'rgba(0, 217, 255, 0.08)',
              border: '1px solid rgba(0, 217, 255, 0.25)'
            }}
          >
            <img 
              src="/vovalyx-logo.png" 
              alt="Vovalyx Logo" 
              style={{ width: '24px', height: '24px', borderRadius: '5px', objectFit: 'contain' }} 
            />
            <span style={{ fontWeight: 800, fontSize: '15px', color: '#fff', letterSpacing: '-0.2px' }}>
              Vovalyx
            </span>
          </div>

          <span style={{ color: '#4B5563' }}>|</span>

          <span
            style={{
              color: '#00D9FF',
              fontSize: '13px',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            Vovalyx — Engineer your vision.
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" y1="14" x2="21" y2="3"></line>
            </svg>
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: '#9CA3AF' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#37D6A0', boxShadow: '0 0 8px #37D6A0' }} />
            Official Platform Partner
          </span>
          <span style={{ color: '#4B5563' }}>•</span>
          <span style={{ color: '#E2E8F0', fontWeight: 500 }}>
            Click to visit www.vovalyx.in ➔
          </span>
        </div>
      </footer>
    </div>
  );
}
