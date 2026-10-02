"use client";

import { memo } from "react";
import { hashString } from "@/lib/format";

/**
 * Original, generative polar artwork used as prototype imagery. Each scene is deterministic for a
 * given seed so the same media record always renders the same picture. These are illustrations,
 * not photographs — real institutional media would replace them via object storage.
 */

type Palette = { sky: [string, string, string]; ice: string; iceShade: string; water: string; mountain: string; mountainFar: string };

const PALETTES: Record<string, Palette> = {
  day: { sky: ["#bfe2ef", "#e4f3f8", "#f7fbfd"], ice: "#f4fafc", iceShade: "#cfe5ee", water: "#2d6f8f", mountain: "#7d98ab", mountainFar: "#a9c3d1" },
  dusk: { sky: ["#2a3f63", "#c97f6b", "#f2c6a0"], ice: "#f3e7e3", iceShade: "#c9b2b4", water: "#3b4f72", mountain: "#4a5674", mountainFar: "#7e7c96" },
  night: { sky: ["#030b16", "#0b1f33", "#12304a"], ice: "#c4d8e4", iceShade: "#7f9db2", water: "#0d2438", mountain: "#1b3248", mountainFar: "#24425d" },
  arctic: { sky: ["#9cc7dc", "#d7ebf2", "#eef6f9"], ice: "#f6fbfd", iceShade: "#cde0e8", water: "#3d7a8f", mountain: "#5d6f74", mountainFar: "#93a7ae" },
  ocean: { sky: ["#6f98b4", "#b9d3e0", "#dfebf1"], ice: "#eef6f9", iceShade: "#bcd6e2", water: "#1d4f6e", mountain: "#567086", mountainFar: "#8aa4b6" },
};

function rng(seed: number) {
  let s = seed || 1;
  return () => {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return ((s >>> 0) % 10000) / 10000;
  };
}

function ridge(r: () => number, y: number, amp: number, w: number, peaks: number) {
  let d = `M0 ${y}`;
  const step = w / peaks;
  for (let i = 0; i <= peaks; i++) {
    const x = i * step;
    const py = y - amp * (0.35 + r() * 0.65);
    d += ` L${(x - step / 2).toFixed(1)} ${py.toFixed(1)} L${x.toFixed(1)} ${(y - amp * r() * 0.3).toFixed(1)}`;
  }
  return d + ` L${w} ${y + 300} L0 ${y + 300} Z`;
}

const W = 800;
const H = 500;

function Sky({ p, id, stars, aurora, r }: { p: Palette; id: string; stars?: boolean; aurora?: boolean; r: () => number }) {
  return (
    <>
      <defs>
        <linearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={p.sky[0]} />
          <stop offset="0.6" stopColor={p.sky[1]} />
          <stop offset="1" stopColor={p.sky[2]} />
        </linearGradient>
        <linearGradient id={`${id}-au`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#4fd1a5" stopOpacity="0" />
          <stop offset="0.55" stopColor="#4fd1a5" stopOpacity="0.55" />
          <stop offset="1" stopColor="#9be7c9" stopOpacity="0" />
        </linearGradient>
        <filter id={`${id}-blur`}><feGaussianBlur stdDeviation="14" /></filter>
      </defs>
      <rect width={W} height={H} fill={`url(#${id}-sky)`} />
      {stars &&
        Array.from({ length: 70 }).map((_, i) => (
          <circle key={i} cx={r() * W} cy={r() * H * 0.55} r={r() * 1.3 + 0.3} fill="#fff" opacity={0.3 + r() * 0.6} />
        ))}
      {aurora && (
        <g filter={`url(#${id}-blur)`} opacity="0.95">
          {[0, 1, 2].map((k) => {
            const y0 = 60 + k * 35 + r() * 30;
            const d = `M-40 ${y0 + 80} C 160 ${y0 - 40}, 330 ${y0 + 120}, 520 ${y0 + 10} S 760 ${y0 - 30}, 860 ${y0 + 50} L 860 ${y0 + 150} C 640 ${y0 + 90}, 420 ${y0 + 200}, 200 ${y0 + 130} S -20 ${y0 + 170}, -40 ${y0 + 160} Z`;
            return <path key={k} d={d} fill={`url(#${id}-au)`} opacity={0.75 - k * 0.18} />;
          })}
        </g>
      )}
    </>
  );
}

function Station({ x, y, s = 1, lit }: { x: number; y: number; s?: number; lit?: boolean }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <rect x="-70" y="-46" width="140" height="40" rx="5" fill="#e9eef1" stroke="#a3b6c3" />
      <rect x="-70" y="-46" width="140" height="10" rx="4" fill="#c4553f" />
      {[-52, -26, 0, 26, 50].map((wx) => (
        <rect key={wx} x={wx - 7} y="-32" width="14" height="10" rx="2" fill={lit ? "#ffd27a" : "#5d7f96"} opacity={lit ? 0.95 : 0.8} />
      ))}
      {[-60, -20, 20, 60].map((lx) => <rect key={lx} x={lx - 2} y="-6" width="4" height="16" fill="#7b8f9c" />)}
      <rect x="78" y="-70" width="3" height="80" fill="#8ea2af" />
      <path d="M81 -70 L106 -62 L81 -55 Z" fill="#1aa3c8" />
      <circle cx="-95" cy="-30" r="14" fill="#f3f6f8" stroke="#a3b6c3" />
      <rect x="-97" y="-16" width="4" height="26" fill="#7b8f9c" />
    </g>
  );
}

function Ship({ x, y, s = 1 }: { x: number; y: number; s?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <path d="M-110 0 L110 0 L92 26 L-96 26 Z" fill="#c4553f" />
      <path d="M-110 0 L110 0 L104 8 L-106 8 Z" fill="#a9452f" />
      <rect x="-40" y="-40" width="80" height="40" rx="3" fill="#f2f5f7" />
      <rect x="-24" y="-66" width="50" height="28" rx="3" fill="#e4eaee" />
      {[-30, -14, 2, 18].map((wx) => <rect key={wx} x={wx} y="-30" width="9" height="7" rx="1.5" fill="#3d566b" />)}
      <rect x="8" y="-92" width="12" height="28" fill="#0b1f33" />
      <rect x="-70" y="-24" width="4" height="24" fill="#8ea2af" />
      <path d="M-68 -24 L-46 -8" stroke="#8ea2af" strokeWidth="2" />
    </g>
  );
}

function Penguin({ x, y, s = 1, flip }: { x: number; y: number; s?: number; flip?: boolean }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${flip ? -s : s} ${s})`}>
      <ellipse cx="0" cy="-22" rx="11" ry="22" fill="#14212c" />
      <ellipse cx="2.5" cy="-18" rx="7" ry="16" fill="#f4f6f7" />
      <circle cx="1" cy="-41" r="7.5" fill="#14212c" />
      <path d="M7 -42 L13 -40 L7 -38 Z" fill="#e0a12b" />
      <circle cx="3.5" cy="-43" r="1.2" fill="#fff" />
      <path d="M-9 -28 Q -16 -14 -11 -4" stroke="#14212c" strokeWidth="4" fill="none" strokeLinecap="round" />
      <path d="M-4 0 L-8 3 M5 0 L9 3" stroke="#e0a12b" strokeWidth="2.5" strokeLinecap="round" />
    </g>
  );
}

function Floes({ r, y0, y1, color, shade, count = 26 }: { r: () => number; y0: number; y1: number; color: string; shade: string; count?: number }) {
  return (
    <g>
      {Array.from({ length: count }).map((_, i) => {
        const cx = r() * W;
        const cy = y0 + r() * (y1 - y0);
        const sc = 0.4 + ((cy - y0) / (y1 - y0)) * 1.2;
        const w = (30 + r() * 70) * sc;
        const h = w * (0.18 + r() * 0.12);
        const pts = Array.from({ length: 7 }).map((_, k) => {
          const a = (k / 7) * Math.PI * 2;
          return `${(cx + Math.cos(a) * w * (0.75 + r() * 0.3)).toFixed(1)},${(cy + Math.sin(a) * h * (0.75 + r() * 0.3)).toFixed(1)}`;
        });
        return (
          <g key={i}>
            <polygon points={pts.join(" ")} fill={shade} transform={`translate(0 ${h * 0.35})`} />
            <polygon points={pts.join(" ")} fill={color} />
          </g>
        );
      })}
    </g>
  );
}

function Mountains({ r, p, base = 300, amp = 120 }: { r: () => number; p: Palette; base?: number; amp?: number }) {
  return (
    <>
      <path d={ridge(r, base - 10, amp * 0.8, W, 7)} fill={p.mountainFar} opacity="0.75" />
      <path d={ridge(r, base + 25, amp, W, 5)} fill={p.mountain} />
      <path d={ridge(r, base + 25, amp * 0.35, W, 9)} fill={p.ice} opacity="0.35" />
    </>
  );
}

function Infographic({ kind, id }: { kind: string; id: string }) {
  const bg = (
    <>
      <rect width={W} height={H} fill="#0b1f33" />
      <rect width={W} height={H} fill={`url(#${id}-grid)`} />
      <defs>
        <pattern id={`${id}-grid`} width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M40 0 L0 0 0 40" fill="none" stroke="#1c4563" strokeWidth="1" />
        </pattern>
      </defs>
    </>
  );
  if (kind === "info-cycle") {
    const months = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];
    return (
      <>
        {bg}
        {months.map((m, i) => {
          const v = 0.5 + 0.45 * Math.cos(((i - 8.5) / 12) * Math.PI * 2);
          const h = 40 + v * 300;
          return (
            <g key={i}>
              <rect x={95 + i * 52} y={430 - h} width="34" height={h} rx="6" fill={v > 0.6 ? "#9fd3e6" : "#1aa3c8"} opacity={0.35 + v * 0.65} />
              <text x={112 + i * 52} y="458" textAnchor="middle" fill="#8fa6b8" fontSize="16" fontFamily="IBM Plex Mono">{m}</text>
            </g>
          );
        })}
        <text x="95" y="70" fill="#eaf3f7" fontSize="30" fontFamily="Source Serif 4">Sea-ice seasonal cycle</text>
        <text x="95" y="100" fill="#4fd1a5" fontSize="15" fontFamily="IBM Plex Mono">WINTER GROWTH · SUMMER RETREAT (ILLUSTRATIVE)</text>
      </>
    );
  }
  if (kind === "info-ozone") {
    return (
      <>
        {bg}
        <circle cx="400" cy="270" r="170" fill="#12304a" stroke="#1aa3c8" strokeWidth="2" />
        <circle cx="400" cy="270" r="120" fill="#1c4563" />
        <ellipse cx="410" cy="275" rx="80" ry="64" fill="#5a4bb5" opacity="0.75" />
        <ellipse cx="410" cy="275" rx="44" ry="34" fill="#8f7ff0" opacity="0.8" />
        <text x="60" y="70" fill="#eaf3f7" fontSize="30" fontFamily="Source Serif 4">The Antarctic ozone hole</text>
        <text x="60" y="100" fill="#4fd1a5" fontSize="15" fontFamily="IBM Plex Mono">FORMS IN AUSTRAL SPRING (SEP–OCT)</text>
      </>
    );
  }
  if (kind === "info-foodweb") {
    const nodes = [["Phytoplankton", 160, 400], ["Krill", 330, 300], ["Fish", 490, 380], ["Penguins", 560, 220], ["Seals", 680, 300], ["Whales", 420, 150]] as const;
    const links = [[0, 1], [1, 2], [1, 3], [2, 3], [2, 4], [1, 5], [3, 4]];
    return (
      <>
        {bg}
        {links.map(([a, b], i) => <line key={i} x1={nodes[a][1]} y1={nodes[a][2]} x2={nodes[b][1]} y2={nodes[b][2]} stroke="#1aa3c8" strokeWidth="2" opacity="0.6" />)}
        {nodes.map(([n, x, y]) => (
          <g key={n}>
            <circle cx={x} cy={y} r="34" fill="#12304a" stroke="#4fd1a5" strokeWidth="2" />
            <text x={x} y={y + 56} textAnchor="middle" fill="#eaf3f7" fontSize="15" fontFamily="IBM Plex Sans">{n}</text>
          </g>
        ))}
        <text x="60" y="70" fill="#eaf3f7" fontSize="30" fontFamily="Source Serif 4">Southern Ocean food web</text>
      </>
    );
  }
  if (kind === "info-compare") {
    return (
      <>
        {bg}
        <circle cx="240" cy="280" r="140" fill="#1c4563" />
        <circle cx="240" cy="280" r="70" fill="#2d6f8f" />
        <circle cx="560" cy="280" r="140" fill="#2d6f8f" />
        <path d="M480 250 Q 520 180 600 200 Q 660 240 640 300 Q 600 360 520 340 Q 470 310 480 250 Z" fill="#eaf3f7" />
        <text x="240" y="460" textAnchor="middle" fill="#eaf3f7" fontSize="18" fontFamily="IBM Plex Sans">Arctic — ocean ringed by land</text>
        <text x="560" y="460" textAnchor="middle" fill="#eaf3f7" fontSize="18" fontFamily="IBM Plex Sans">Antarctic — land ringed by ocean</text>
        <text x="60" y="70" fill="#eaf3f7" fontSize="30" fontFamily="Source Serif 4">Arctic vs Antarctic</text>
      </>
    );
  }
  // info-map
  const pts = [["Maitri", 300, 360], ["Bharati", 420, 330], ["Himadri", 520, 120], ["Himansh", 600, 250]] as const;
  return (
    <>
      {bg}
      <circle cx="360" cy="330" r="120" fill="#12304a" stroke="#1c4563" />
      <circle cx="540" cy="130" r="80" fill="#12304a" stroke="#1c4563" />
      {pts.map(([n, x, y]) => (
        <g key={n}>
          <circle cx={x} cy={y} r="9" fill="#4fd1a5" />
          <circle cx={x} cy={y} r="18" fill="none" stroke="#4fd1a5" opacity="0.5" />
          <text x={x + 24} y={y + 6} fill="#eaf3f7" fontSize="18" fontFamily="IBM Plex Sans">{n}</text>
        </g>
      ))}
      <text x="60" y="70" fill="#eaf3f7" fontSize="30" fontFamily="Source Serif 4">India&apos;s polar research stations</text>
    </>
  );
}

function SceneBody({ scene, seed, id }: { scene: string; seed: number; id: string }) {
  const r = rng(seed);
  if (scene.startsWith("info-")) return <Infographic kind={scene} id={id} />;

  const night = ["aurora", "station-night", "night"].includes(scene);
  const p = night ? PALETTES.night : ["arctic-village", "tundra", "fjord", "glacier"].includes(scene) ? PALETTES.arctic
    : ["ocean", "ctd", "krill", "ship"].includes(scene) ? PALETTES.ocean : scene === "balloon" ? PALETTES.dusk : PALETTES.day;
  const sky = Sky({ p, id, r, stars: night, aurora: scene === "aurora" || scene === "station-night" });

  switch (scene) {
    case "krill":
      return (
        <>
          <defs>
            <linearGradient id={`${id}-sea`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#2b7a99" /><stop offset="1" stopColor="#061423" />
            </linearGradient>
          </defs>
          <rect width={W} height={H} fill={`url(#${id}-sea)`} />
          {Array.from({ length: 140 }).map((_, i) => {
            const x = 120 + r() * 560, y = 80 + r() * 340, a = r() * 360;
            return <path key={i} d="M0 0 q 7 -5 14 0" stroke="#f0a58f" strokeWidth="2.2" fill="none" opacity={0.5 + r() * 0.5} transform={`translate(${x} ${y}) rotate(${a})`} />;
          })}
        </>
      );
    case "microscope":
      return (
        <>
          <rect width={W} height={H} fill="#0d2a2a" />
          <circle cx="400" cy="250" r="230" fill="#123b36" />
          {Array.from({ length: 60 }).map((_, i) => (
            <ellipse key={i} cx={200 + r() * 400} cy={60 + r() * 380} rx={6 + r() * 26} ry={3 + r() * 8} fill={r() > 0.5 ? "#4fd1a5" : "#2a9d8f"} opacity={0.4 + r() * 0.5} transform={`rotate(${r() * 180} ${400} ${250})`} />
          ))}
          <circle cx="400" cy="250" r="230" fill="none" stroke="#061423" strokeWidth="60" />
        </>
      );
    case "rocks":
      return (
        <>
          <rect width={W} height={H} fill="#d9d4cc" />
          {Array.from({ length: 16 }).map((_, i) => {
            const y = i * 34 - 20;
            return <path key={i} d={`M-20 ${y} C 200 ${y + 60 * r()}, 420 ${y - 70 * r()}, 820 ${y + 30}`} stroke={i % 3 === 0 ? "#6d6259" : i % 3 === 1 ? "#a39687" : "#4b4741"} strokeWidth={10 + r() * 14} fill="none" opacity="0.85" />;
          })}
        </>
      );
    case "lichen":
      return (
        <>
          <rect width={W} height={H} fill="#8a8f8f" />
          {Array.from({ length: 22 }).map((_, i) => <ellipse key={i} cx={r() * W} cy={r() * H} rx={60 + r() * 120} ry={30 + r() * 60} fill={["#7a807f", "#9aa09d", "#6c7270"][i % 3]} />)}
          {Array.from({ length: 70 }).map((_, i) => <circle key={`l${i}`} cx={r() * W} cy={r() * H} r={4 + r() * 18} fill={["#d9a531", "#c4553f", "#e5d17b", "#6b8f4e"][Math.floor(r() * 4)]} opacity={0.75} />)}
        </>
      );
    default:
      break;
  }

  const horizon = 300;
  const elements: React.ReactNode[] = [];
  const hasMountains = ["arctic-village", "fjord", "glacier", "mountains", "oasis", "tundra", "station", "station-night", "drill", "team", "solar", "lake", "blizzard", "instrument", "aurora", "night"].includes(scene);
  if (hasMountains) elements.push(<g key="m">{Mountains({ r, p, base: scene === "mountains" ? 280 : 300, amp: scene === "mountains" || scene === "fjord" ? 170 : 90 })}</g>);

  const water = ["seaice", "pancake", "ship", "iceberg", "iceshelf", "ocean", "ctd", "fjord", "glacier", "penguins", "seal"].includes(scene);
  if (water) elements.push(<rect key="w" y={horizon} width={W} height={H - horizon} fill={p.water} />);
  else elements.push(<path key="g" d={`M0 ${horizon + 20} Q 400 ${horizon - 10} 800 ${horizon + 25} L800 500 L0 500 Z`} fill={scene === "tundra" ? "#7f9a6a" : scene === "oasis" || scene === "lake" ? "#8d8579" : p.ice} />);

  switch (scene) {
    case "seaice":
      elements.push(<g key="f">{Floes({ r, y0: horizon + 10, y1: H, color: p.ice, shade: p.iceShade, count: 34 })}</g>);
      break;
    case "pancake":
      for (let i = 0; i < 55; i++) {
        const cx = r() * W, cy = horizon + 10 + r() * 190, s = 0.5 + ((cy - horizon) / 200) * 1.4;
        elements.push(<ellipse key={`p${i}`} cx={cx} cy={cy} rx={26 * s} ry={9 * s} fill={p.ice} stroke={p.iceShade} strokeWidth={3 * s} />);
      }
      break;
    case "ship":
      elements.push(<g key="f">{Floes({ r, y0: horizon + 30, y1: H, color: p.ice, shade: p.iceShade, count: 18 })}</g>);
      elements.push(<Ship key="s" x={420} y={horizon + 30} s={1.1} />);
      break;
    case "iceberg":
    case "iceshelf":
      elements.push(<path key="b" d={scene === "iceshelf" ? `M0 ${horizon - 90} L800 ${horizon - 70} L800 ${horizon + 20} L0 ${horizon + 20} Z` : `M200 ${horizon} L230 ${horizon - 110} L560 ${horizon - 120} L600 ${horizon} Z`} fill={p.ice} />);
      elements.push(<path key="bs" d={scene === "iceshelf" ? `M0 ${horizon - 40} L800 ${horizon - 30} L800 ${horizon + 20} L0 ${horizon + 20} Z` : `M230 ${horizon - 110} L250 ${horizon} L200 ${horizon} Z`} fill={p.iceShade} opacity="0.8" />);
      elements.push(<path key="bu" d={`M210 ${horizon + 5} L590 ${horizon + 5} L520 ${horizon + 90} L280 ${horizon + 80} Z`} fill="#5ba6c2" opacity="0.35" />);
      break;
    case "ocean":
      for (let i = 0; i < 9; i++) elements.push(<path key={`wv${i}`} d={`M0 ${horizon + 20 + i * 22} Q 100 ${horizon + 8 + i * 22} 200 ${horizon + 20 + i * 22} T 400 ${horizon + 20 + i * 22} T 600 ${horizon + 20 + i * 22} T 800 ${horizon + 20 + i * 22}`} stroke="#9fd3e6" strokeOpacity={0.15 + i * 0.04} strokeWidth="3" fill="none" />);
      break;
    case "ctd":
      elements.push(<Ship key="s" x={250} y={horizon + 10} s={0.8} />);
      elements.push(<line key="l" x1={340} y1={horizon - 30} x2={420} y2={horizon + 120} stroke="#0b1f33" strokeWidth="2" />);
      elements.push(<g key="r" transform={`translate(420 ${horizon + 150})`}><rect x="-26" y="-30" width="52" height="60" rx="6" fill="#c9d6de" stroke="#0b1f33" />{[-16, -5, 6, 17].map((x) => <rect key={x} x={x - 3} y="-26" width="6" height="52" fill="#3d566b" />)}</g>);
      break;
    case "penguins":
      elements.push(<rect key="ice" y={horizon + 60} width={W} height={H} fill={p.ice} />);
      for (let i = 0; i < 9; i++) elements.push(<Penguin key={`pg${i}`} x={140 + i * 66 + r() * 20} y={horizon + 150 + r() * 70} s={1 + r() * 0.6} flip={r() > 0.5} />);
      break;
    case "seal":
      elements.push(<rect key="ice" y={horizon + 40} width={W} height={H} fill={p.ice} />);
      elements.push(<ellipse key="hole" cx="560" cy={horizon + 140} rx="60" ry="16" fill={p.water} />);
      elements.push(<g key="sl" transform={`translate(330 ${horizon + 150})`}><ellipse cx="0" cy="0" rx="120" ry="34" fill="#4a5560" /><ellipse cx="-100" cy="-10" rx="38" ry="28" fill="#4a5560" /><circle cx="-118" cy="-16" r="3" fill="#0b1f33" /><path d="M110 0 L150 -14 L150 14 Z" fill="#3b444d" /></g>);
      break;
    case "station":
    case "station-night":
      elements.push(<Station key="st" x={400} y={horizon + 60} s={1.2} lit={scene === "station-night"} />);
      break;
    case "arctic-village":
      for (let i = 0; i < 6; i++) elements.push(<rect key={`h${i}`} x={140 + i * 95} y={horizon + 20 - (i % 2) * 10} width="70" height="42" fill={["#c4553f", "#e0a12b", "#2d6f8f", "#f2f5f7"][i % 4]} />);
      break;
    case "fjord":
    case "glacier":
      elements.push(<path key="gl" d={`M260 ${horizon - 80} L540 ${horizon - 70} L600 ${horizon + 8} L200 ${horizon + 8} Z`} fill={p.ice} />);
      elements.push(<path key="gls" d={`M200 ${horizon + 8} L600 ${horizon + 8} L590 ${horizon + 30} L210 ${horizon + 30} Z`} fill={p.iceShade} />);
      elements.push(<g key="f">{Floes({ r, y0: horizon + 40, y1: H, color: p.ice, shade: p.iceShade, count: 12 })}</g>);
      break;
    case "balloon":
      elements.push(<g key="bl"><line x1="400" y1="140" x2="400" y2="260" stroke="#3d566b" strokeWidth="1.5" /><ellipse cx="400" cy="100" rx="46" ry="56" fill="#f6f2ee" /><rect x="392" y="258" width="16" height="14" fill="#c4553f" /></g>);
      elements.push(<Station key="st" x={250} y={horizon + 50} s={0.7} />);
      break;
    case "instrument":
    case "solar":
      for (let i = 0; i < 5; i++) elements.push(<g key={`sp${i}`} transform={`translate(${170 + i * 115} ${horizon + 90})`}><path d="M-44 0 L44 0 L30 -46 L-30 -46 Z" fill={scene === "solar" ? "#1c4563" : "#c9d6de"} stroke="#5b7489" /><rect x="-2" y="0" width="4" height="30" fill="#5b7489" /></g>);
      break;
    case "drill":
    case "team":
      elements.push(<g key="tri" transform={`translate(400 ${horizon + 110})`}><path d="M-60 40 L0 -110 L60 40" stroke="#c4553f" strokeWidth="6" fill="none" /><rect x="-6" y="-60" width="12" height="100" fill="#3d566b" /></g>);
      for (let i = 0; i < (scene === "team" ? 6 : 2); i++) elements.push(<g key={`pp${i}`} transform={`translate(${200 + i * 80} ${horizon + 150})`}><circle cx="0" cy="-58" r="10" fill="#e0a12b" /><rect x="-14" y="-48" width="28" height="44" rx="8" fill={["#c4553f", "#1aa3c8", "#e0a12b"][i % 3]} /><rect x="-12" y="-6" width="10" height="26" fill="#0b1f33" /><rect x="2" y="-6" width="10" height="26" fill="#0b1f33" /></g>);
      break;
    case "lake":
    case "oasis":
      elements.push(<ellipse key="lk" cx="400" cy={horizon + 110} rx="260" ry="50" fill="#bfe2ef" />);
      elements.push(<ellipse key="lk2" cx="400" cy={horizon + 110} rx="200" ry="34" fill="#dff1f7" />);
      break;
    case "blizzard":
      for (let i = 0; i < 160; i++) {
        const x = r() * W, y = r() * H;
        elements.push(<line key={`bz${i}`} x1={x} y1={y} x2={x + 40 + r() * 50} y2={y + 6} stroke="#fff" strokeOpacity={0.3 + r() * 0.5} strokeWidth={1 + r() * 2} />);
      }
      elements.push(<rect key="haze" width={W} height={H} fill="#e8f1f5" opacity="0.35" />);
      break;
    case "tundra":
      for (let i = 0; i < 40; i++) elements.push(<circle key={`t${i}`} cx={r() * W} cy={horizon + 40 + r() * 160} r={4 + r() * 10} fill={["#a5b77d", "#6b8f4e", "#d2c27a"][i % 3]} />);
      break;
    default:
      break;
  }
  return (
    <>
      {sky}
      {elements}
    </>
  );
}

function PolarSceneInner({ scene, seed, className, title }: { scene: string; seed?: string; className?: string; title?: string }) {
  const s = hashString(`${scene}:${seed || scene}`);
  const id = `ps${s.toString(36)}`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice" className={className} role="img" aria-label={title ? `Illustration: ${title}` : "Polar illustration"}>
      <SceneBody scene={scene} seed={s} id={id} />
    </svg>
  );
}

export const PolarScene = memo(PolarSceneInner);
