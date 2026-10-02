import { BRAND } from "@/lib/format";

/** Original mark: a polar compass ring, six-arm snowflake/meridian star and a data node. */
export function LogoMark({ size = 32, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" className={className} aria-hidden>
      <defs>
        <linearGradient id="pn-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#9fd3e6" />
          <stop offset="1" stopColor="#1aa3c8" />
        </linearGradient>
      </defs>
      <circle cx="20" cy="20" r="17.5" fill="none" stroke="url(#pn-g)" strokeWidth="1.6" />
      <circle cx="20" cy="20" r="12" fill="none" stroke="#9fd3e6" strokeOpacity="0.45" strokeWidth="0.9" strokeDasharray="1.6 2.4" />
      {[0, 60, 120].map((a) => (
        <g key={a} transform={`rotate(${a} 20 20)`}>
          <line x1="20" y1="5.5" x2="20" y2="34.5" stroke="url(#pn-g)" strokeWidth="1.7" strokeLinecap="round" />
          <path d="M17.6 9.2 L20 11.4 L22.4 9.2 M17.6 30.8 L20 28.6 L22.4 30.8" fill="none" stroke="#9fd3e6" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
        </g>
      ))}
      <path d="M20 2 L21.3 5 L20 4.4 L18.7 5 Z" fill="#e8f6fb" />
      <circle cx="20" cy="20" r="3.1" fill="#0b1f33" stroke="#4fd1a5" strokeWidth="1.4" />
      <circle cx="31.6" cy="11.4" r="2.1" fill="#4fd1a5" />
      <line x1="22.4" y1="18.2" x2="30" y2="12.6" stroke="#4fd1a5" strokeWidth="0.9" strokeOpacity="0.8" />
    </svg>
  );
}

export function Logo({ dark = true, compact = false }: { dark?: boolean; compact?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark size={compact ? 28 : 34} />
      {!compact && (
        <span className="leading-none">
          <span className={`block font-display text-[19px] font-semibold tracking-tight ${dark ? "text-white" : "text-night"}`}>{BRAND}</span>
          <span className={`mt-1 block font-mono text-[9.5px] uppercase tracking-[0.2em] ${dark ? "text-glacier/70" : "text-steel"}`}>Polar Knowledge Platform</span>
        </span>
      )}
    </span>
  );
}
