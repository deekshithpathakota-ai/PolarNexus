"use client";

import { useEffect, useRef } from "react";

/**
 * Sign-in backdrop — layered, restrained and cheap to render:
 *   dark polar sky → ice-shelf silhouette → aurora (CSS-animated blurred gradients) → snow & observation
 *   particles (one small canvas) → faint polar coordinate grid (SVG).
 * Respects prefers-reduced-motion (a single static frame, no animation), pauses when the tab is hidden,
 * scales particle count with screen size and caps the frame rate at ~30 fps.
 */
export function PolarBackdrop() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let w = 0, h = 0, dpr = 1, raf = 0, last = 0;
    type P = { x: number; y: number; r: number; vx: number; vy: number; a: number; kind: "snow" | "data"; tw: number };
    let parts: P[] = [];

    const build = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const area = (w * h) / 1_000_000;
      const small = w < 640;
      const nSnow = Math.round(Math.min(small ? 28 : 70, 40 * area));
      const nData = Math.round(Math.min(small ? 10 : 26, 14 * area));
      parts = [
        ...Array.from({ length: nSnow }, () => ({ x: Math.random() * w, y: Math.random() * h, r: 0.6 + Math.random() * 1.4,
          vx: -0.08 + Math.random() * 0.16, vy: 0.12 + Math.random() * 0.28, a: 0.25 + Math.random() * 0.5, kind: "snow" as const, tw: Math.random() * 6 })),
        ...Array.from({ length: nData }, () => ({ x: Math.random() * w, y: h * (0.15 + Math.random() * 0.6), r: 1.4 + Math.random() * 1.2,
          vx: -0.05 + Math.random() * 0.1, vy: -0.03 + Math.random() * 0.06, a: 0.5 + Math.random() * 0.4, kind: "data" as const, tw: Math.random() * 6 })),
      ];
    };

    const draw = (t: number) => {
      ctx.clearRect(0, 0, w, h);
      const data = parts.filter((p) => p.kind === "data");
      // faint links between nearby observation points ("a network of measurements")
      for (let i = 0; i < data.length; i++) {
        for (let j = i + 1; j < data.length; j++) {
          const dx = data[i].x - data[j].x, dy = data[i].y - data[j].y;
          const d = Math.hypot(dx, dy);
          if (d < 150) {
            ctx.strokeStyle = `rgba(159, 211, 230, ${0.12 * (1 - d / 150)})`;
            ctx.lineWidth = 0.6;
            ctx.beginPath();
            ctx.moveTo(data[i].x, data[i].y);
            ctx.lineTo(data[j].x, data[j].y);
            ctx.stroke();
          }
        }
      }
      for (const p of parts) {
        const twinkle = p.kind === "data" ? 0.75 + 0.25 * Math.sin(t / 1400 + p.tw) : 1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.kind === "snow" ? `rgba(234, 243, 247, ${p.a})` : `rgba(79, 209, 165, ${p.a * twinkle})`;
        ctx.fill();
        if (p.kind === "data") {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r + 3, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(79, 209, 165, ${0.18 * twinkle})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    };

    const step = (t: number) => {
      raf = requestAnimationFrame(step);
      if (t - last < 33) return; // ~30 fps is plenty for slow drift
      last = t;
      for (const p of parts) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.kind === "snow") {
          p.x += Math.sin((t / 3000) + p.tw) * 0.08;
          if (p.y > h + 4) { p.y = -4; p.x = Math.random() * w; }
        } else if (p.y < h * 0.1 || p.y > h * 0.8) p.vy *= -1;
        if (p.x < -4) p.x = w + 4;
        if (p.x > w + 4) p.x = -4;
      }
      draw(t);
    };

    build();
    draw(0);
    const onResize = () => { build(); draw(performance.now()); };
    const onVis = () => {
      cancelAnimationFrame(raf);
      if (!document.hidden && !reduce) raf = requestAnimationFrame(step);
    };
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVis);
    if (!reduce) raf = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden bg-[radial-gradient(120%_90%_at_70%_0%,#12304a_0%,#0b1f33_45%,#061423_100%)]">
      {/* aurora — three slow, blurred bands; no flashing */}
      <div className="pn-aurora pn-aurora-1" />
      <div className="pn-aurora pn-aurora-2" />
      <div className="pn-aurora pn-aurora-3" />
      {/* polar coordinate grid (azimuthal graticule) */}
      <svg className="pn-grid absolute -bottom-[38vmax] -left-[22vmax] h-[110vmax] w-[110vmax] opacity-[0.16]" viewBox="-100 -100 200 200">
        <g fill="none" stroke="#9fd3e6" strokeWidth="0.15">
          {[15, 30, 45, 60, 75, 90].map((r) => <circle key={r} r={r} strokeDasharray={r % 30 ? "0.6 1.4" : undefined} />)}
          {Array.from({ length: 24 }, (_, i) => {
            const a = (i * 15 * Math.PI) / 180;
            return <line key={i} x1={0} y1={0} x2={Math.cos(a) * 90} y2={Math.sin(a) * 90} strokeOpacity={i % 6 ? 0.5 : 1} />;
          })}
        </g>
        <circle r="1.2" fill="#4fd1a5" />
      </svg>
      {/* ice shelf & mountains */}
      <svg className="absolute inset-x-0 bottom-0 h-[34vh] w-full" viewBox="0 0 1440 320" preserveAspectRatio="none">
        <defs>
          <linearGradient id="pn-ice-far" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1c4563" /><stop offset="1" stopColor="#0b1f33" /></linearGradient>
          <linearGradient id="pn-ice-near" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#d5e6ee" stopOpacity="0.22" /><stop offset="1" stopColor="#0b1f33" stopOpacity="0" /></linearGradient>
        </defs>
        <path d="M0 210 L120 150 L210 185 L320 120 L420 175 L520 135 L640 190 L760 140 L880 180 L1000 125 L1120 170 L1240 140 L1340 175 L1440 150 L1440 320 L0 320 Z" fill="url(#pn-ice-far)" opacity="0.75" />
        <path d="M0 250 L180 238 L360 246 L560 232 L760 244 L980 236 L1200 246 L1440 238 L1440 320 L0 320 Z" fill="#061423" />
        <path d="M0 250 L180 238 L360 246 L560 232 L760 244 L980 236 L1200 246 L1440 238" fill="none" stroke="#9fd3e6" strokeOpacity="0.35" strokeWidth="1.2" />
        <rect x="0" y="238" width="1440" height="40" fill="url(#pn-ice-near)" />
      </svg>
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
      <div className="grain absolute inset-0 opacity-40" />
    </div>
  );
}
