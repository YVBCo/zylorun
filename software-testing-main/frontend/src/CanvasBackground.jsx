import React, { useEffect, useRef } from 'react';

class BgErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-gray-800 to-[#0b1220]" />;
    }
    return this.props.children;
  }
}

const CanvasBackgroundBase = ({ mousePos, isMobile, reducedMotion, isKonami }) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (reducedMotion) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d', { alpha: false });
    let animationFrameId;
    let lastTime = 0;
    
    // Matrix characters
    const chars = "0123456789ABCDEF".split("");
    let columns = [];
    const fontSize = 14;

    // Particles
    const maxParticles = isMobile ? 20 : 60;
    let particles = [];

    let width, height;

    const init = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5); // Cap DPR
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
      
      const cols = Math.floor(width / fontSize);
      columns = Array(cols).fill(1).map(() => Math.random() * -100);

      particles = Array(maxParticles).fill().map(() => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        life: Math.random(),
        color: Math.random() > 0.5 ? '#00e5ff' : '#22c55e'
      }));
    };

    const drawGrid = (t) => {
      ctx.strokeStyle = isKonami ? 'rgba(34, 197, 94, 0.05)' : 'rgba(0, 229, 255, 0.03)';
      ctx.lineWidth = 1;
      const gridSize = 40;
      const offsetX = (t / 50) % gridSize;
      const offsetY = (t / 50) % gridSize;

      ctx.beginPath();
      for (let x = -offsetX; x < width; x += gridSize) {
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
      }
      for (let y = -offsetY; y < height; y += gridSize) {
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
      }
      ctx.stroke();

      // Intersections repelling near mouse
      if (!isMobile) {
        ctx.fillStyle = isKonami ? 'rgba(34, 197, 94, 0.3)' : 'rgba(0, 229, 255, 0.3)';
        for (let x = -offsetX; x < width; x += gridSize) {
          for (let y = -offsetY; y < height; y += gridSize) {
            const dx = x - mousePos.x;
            const dy = y - mousePos.y;
            const dist = Math.sqrt(dx*dx + dy*dy);
            if (dist < 150) {
              const repel = (150 - dist) / 150;
              ctx.beginPath();
              ctx.arc(x + dx * repel * 0.1, y + dy * repel * 0.1, 1.5, 0, Math.PI * 2);
              ctx.fill();
            }
          }
        }
      }
    };

    const drawParticles = (dt) => {
      particles.forEach(p => {
        p.x += p.vx * dt * 60;
        p.y += p.vy * dt * 60;
        p.life -= dt * 0.2;
        if (p.life <= 0 || p.x < 0 || p.x > width || p.y < 0 || p.y > height) {
          p.x = Math.random() * width;
          p.y = Math.random() * height;
          p.life = 1;
        }
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.life * 0.5;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.5, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1.0;
    };

    const drawMatrix = () => {
      ctx.fillStyle = isKonami ? 'rgba(34, 197, 94, 0.15)' : 'rgba(0, 229, 255, 0.05)';
      ctx.font = `${fontSize}px monospace`;
      
      const edge = Math.floor(width * 0.15 / fontSize); // Only draw on 15% edges
      
      columns.forEach((y, i) => {
        if (i > edge && i < columns.length - edge) return;
        
        const text = chars[Math.floor(Math.random() * chars.length)];
        ctx.fillText(text, i * fontSize, y * fontSize);
        
        if (y * fontSize > height && Math.random() > 0.975) {
          columns[i] = 0;
        }
        columns[i]++;
      });
    };

    let isVisible = true;
    const handleVisibility = () => { isVisible = !document.hidden; };
    document.addEventListener("visibilitychange", handleVisibility);

    const render = (time) => {
      const dt = (time - lastTime) / 1000;
      lastTime = time;

      if (isVisible) {
        // Clear with fade for trails
        ctx.fillStyle = isKonami ? 'rgba(0, 10, 0, 0.2)' : 'rgba(11, 18, 32, 0.2)';
        ctx.fillRect(0, 0, width, height);

        drawGrid(time);
        drawParticles(dt);
        drawMatrix();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    init();
    window.addEventListener('resize', init);
    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', init);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [mousePos, isMobile, reducedMotion, isKonami]);

  if (reducedMotion) {
    return <div className="absolute inset-0 bg-[#0b1220] bg-[linear-gradient(rgba(0,229,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,229,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px]" />;
  }

  return (
    <>
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
      {/* Radar sweep */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-[0.03]"
        style={{
          background: isKonami 
            ? 'conic-gradient(from 0deg at 50% 50%, transparent 0deg, rgba(34,197,94,1) 360deg)' 
            : 'conic-gradient(from 0deg at 50% 50%, transparent 0deg, rgba(0,229,255,1) 360deg)',
          animation: 'spin 4s linear infinite'
        }}
      />
      {/* Scanline */}
      <div className={`absolute inset-0 pointer-events-none bg-gradient-to-b from-transparent via-${isKonami ? 'green' : 'cyan'}-500/10 to-transparent h-4 w-full animate-[scanline_6s_linear_infinite]`} />
      {/* Vignette */}
      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_150px_rgba(0,0,0,0.9)]" />
    </>
  );
};

export default function CanvasBackground(props) {
  return (
    <BgErrorBoundary>
      <CanvasBackgroundBase {...props} />
    </BgErrorBoundary>
  );
}
