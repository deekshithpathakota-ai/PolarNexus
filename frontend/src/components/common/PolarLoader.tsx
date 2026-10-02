import clsx from "clsx";

/** Lightweight PolarNexus loading mark: observation points orbiting a pole. Static under reduced motion. */
export function PolarLoader({ label = "Initializing PolarNexus", size = 56, className, dark = true }: {
  label?: string; size?: number; className?: string; dark?: boolean;
}) {
  return (
    <div role="status" aria-live="polite" className={clsx("flex flex-col items-center gap-3", className)}>
      <span className="relative block" style={{ width: size, height: size }} aria-hidden>
        <span className="absolute inset-0 rounded-full border border-glacier/30" />
        <span className="absolute inset-[22%] rounded-full border border-dashed border-glacier/25" />
        <span className="pn-orbit absolute inset-0">
          {[0, 72, 144, 216, 288].map((a, i) => (
            <span key={a} className="absolute left-1/2 top-1/2 h-1.5 w-1.5 rounded-full bg-aurora"
              style={{ transform: `rotate(${a}deg) translateY(-${size / 2 - 3}px)`, opacity: 0.35 + i * 0.15, marginLeft: -3, marginTop: -3 }} />
          ))}
        </span>
        <span className="absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan shadow-[0_0_12px_#1aa3c8]" />
      </span>
      {label && <span className={clsx("font-mono text-[11px] uppercase tracking-[0.2em]", dark ? "text-glacier/80" : "text-steel")}>{label}</span>}
    </div>
  );
}
