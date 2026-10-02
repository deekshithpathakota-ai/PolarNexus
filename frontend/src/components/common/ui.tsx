"use client";

import clsx from "clsx";
import {
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  FlaskConical,
  Inbox,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import { STATUS_LABEL } from "@/lib/format";

/* ------------------------------------------------------------------ Button */
type Variant = "primary" | "secondary" | "ghost" | "danger" | "dark" | "subtle";
const variants: Record<Variant, string> = {
  primary: "bg-cyan-deep text-white hover:bg-[#0c6f8e] shadow-sm",
  secondary: "bg-white text-night border border-frost hover:border-glacier hover:bg-ice",
  ghost: "text-ink-soft hover:bg-ice hover:text-night",
  danger: "bg-coral text-white hover:bg-[#a9452f]",
  dark: "bg-night text-white hover:bg-deep",
  subtle: "bg-ice text-deep hover:bg-frost",
};

export function Button({
  variant = "primary",
  size = "md",
  loading,
  icon,
  className,
  children,
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" | "lg"; loading?: boolean; icon?: ReactNode }) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex select-none items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-55",
        size === "sm" && "h-8 px-3 text-[13px]",
        size === "md" && "h-10 px-4 text-sm",
        size === "lg" && "h-12 px-5 text-[15px]",
        variants[variant],
        className,
      )}
    >
      {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : icon}
      {children}
    </button>
  );
}

export function LinkButton({ href, variant = "primary", size = "md", icon, children, className }: {
  href: string; variant?: Variant; size?: "sm" | "md" | "lg"; icon?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <Link
      href={href}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors",
        size === "sm" && "h-8 px-3 text-[13px]",
        size === "md" && "h-10 px-4 text-sm",
        size === "lg" && "h-12 px-5 text-[15px]",
        variants[variant],
        className,
      )}
    >
      {icon}
      {children}
    </Link>
  );
}

/* ------------------------------------------------------------------ Card / Badge / Chip */
export function Card({ className, children, as: As = "div", ...rest }: { className?: string; children: ReactNode; as?: "div" | "section" | "article" } & Record<string, unknown>) {
  return (
    <As {...rest} className={clsx("rounded-2xl border border-frost bg-white shadow-card", className)}>
      {children}
    </As>
  );
}

const tones = {
  slate: "bg-ice text-ink-soft border-frost",
  cyan: "bg-[#e3f4fa] text-cyan-deep border-[#c2e6f2]",
  teal: "bg-[#e2f4f1] text-teal border-[#bfe5df]",
  amber: "bg-[#fbf1df] text-[#8a5c0c] border-[#f0dcb4]",
  coral: "bg-[#fbe9e5] text-coral border-[#f2cfc6]",
  night: "bg-night text-white border-night",
  violet: "bg-[#efedfb] text-[#5a4bb5] border-[#dcd7f5]",
};
export type Tone = keyof typeof tones;

export function Badge({ tone = "slate", children, className, icon }: { tone?: Tone; children: ReactNode; className?: string; icon?: ReactNode }) {
  return (
    <span className={clsx("inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11.5px] font-medium", tones[tone], className)}>
      {icon}
      {children}
    </span>
  );
}

export function DemoBadge({ label = "Demo data", className }: { label?: string; className?: string }) {
  return (
    <span
      title="Prototype demonstration data — not an official institutional record"
      className={clsx("inline-flex items-center gap-1 rounded-full border border-dashed border-[#e2c58f] bg-[#fdf8ee] px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-wide text-[#8a5c0c]", className)}
    >
      <FlaskConical className="h-3 w-3" />
      {label}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const tone: Tone =
    status === "published" ? "teal" : status === "approved" ? "cyan" : status === "under_review" ? "violet"
      : status === "changes_requested" ? "amber" : status === "rejected" ? "coral" : "slate";
  return (
    <Badge tone={tone} icon={status === "evidence_checked" ? <ShieldCheck className="h-3 w-3 text-teal" /> : undefined}>
      {STATUS_LABEL[status] || status}
    </Badge>
  );
}

export function Chip({ active, children, onClick, onRemove }: { active?: boolean; children: ReactNode; onClick?: () => void; onRemove?: () => void }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border text-[13px] transition-colors",
        active ? "border-cyan bg-[#e3f4fa] text-cyan-deep" : "border-frost bg-white text-ink-soft hover:border-glacier",
      )}
    >
      <button type="button" onClick={onClick} className="px-3 py-1" aria-pressed={active}>
        {children}
      </button>
      {onRemove && (
        <button type="button" onClick={onRemove} aria-label="Remove filter" className="-ml-1 pr-2 text-mist hover:text-night">
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </span>
  );
}

/* ------------------------------------------------------------------ Tooltip (info) */
export function InfoTip({ text, label }: { text: string; label?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span className="relative inline-flex align-middle" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        aria-describedby={id}
        aria-label={label ? `What is ${label}?` : "More information"}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((o) => !o)}
        className="text-mist hover:text-cyan-deep"
      >
        <CircleHelp className="h-3.5 w-3.5" />
      </button>
      <span
        id={id}
        role="tooltip"
        className={clsx(
          "absolute bottom-full left-1/2 z-50 mb-2 w-60 -translate-x-1/2 rounded-lg bg-night px-3 py-2 text-left text-xs font-normal leading-relaxed text-white shadow-lift transition-opacity",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      >
        {label && <strong className="mb-0.5 block font-semibold text-glacier">{label}</strong>}
        {text}
      </span>
    </span>
  );
}

export const GLOSSARY = {
  hybrid: "Combines keyword (full-text) matching with semantic vector similarity, merged by reciprocal rank fusion.",
  semantic: "Finds passages with similar meaning using vector embeddings, even when the exact words differ.",
  keyword: "Classic full-text search that matches the words you type (with stemming).",
  rag: "Retrieval-Augmented Generation: the assistant first retrieves repository passages, then answers only from them, with citations.",
  evidence: "The passages from repository records that support an answer. Every [n] marker links to one.",
  metadata: "Structured descriptive fields — title, region, year, authors, topics — that make resources findable.",
  vector: "Each passage is converted to a numeric vector; nearby vectors have similar meaning.",
};

/* ------------------------------------------------------------------ States */
export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("skeleton rounded-lg", className)} aria-hidden />;
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <Card className="p-5">
      <Skeleton className="mb-3 h-4 w-24" />
      <Skeleton className="mb-2 h-5 w-3/4" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="mb-2 h-3.5 w-full" />
      ))}
    </Card>
  );
}

export function EmptyState({ title, body, action, icon }: { title: string; body?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-frost bg-white/60 px-6 py-14 text-center">
      <div className="mb-3 rounded-full bg-ice p-3 text-steel">{icon || <Inbox className="h-6 w-6" />}</div>
      <p className="font-display text-lg text-night">{title}</p>
      {body && <p className="mt-1 max-w-md text-sm text-ink-soft">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, compact }: { error: { message: string; status?: number } | string; onRetry?: () => void; compact?: boolean }) {
  const msg = typeof error === "string" ? error : error.message;
  const status = typeof error === "string" ? undefined : error.status;
  const title = status === 404 ? "Not found" : status === 403 ? "Access restricted" : status === 401 ? "Sign in required" : "Something went wrong";
  return (
    <div role="alert" className={clsx("flex flex-col items-center rounded-2xl border border-[#f2cfc6] bg-[#fdf6f4] text-center", compact ? "px-4 py-6" : "px-6 py-12")}>
      <TriangleAlert className="mb-2 h-6 w-6 text-coral" />
      <p className="font-display text-lg text-night">{title}</p>
      <p className="mt-1 max-w-md text-sm text-ink-soft">{msg}</p>
      <div className="mt-4 flex gap-2">
        {onRetry && status !== 404 && status !== 403 && (
          <Button variant="secondary" size="sm" onClick={onRetry} icon={<RefreshCw className="h-3.5 w-3.5" />}>
            Retry
          </Button>
        )}
        {status === 401 && <LinkButton href="/login" size="sm">Sign in</LinkButton>}
      </div>
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-steel" role="status">
      <LoaderCircle className="h-4 w-4 animate-spin" /> {label || "Loading…"}
    </div>
  );
}

/* ------------------------------------------------------------------ Pagination */
export function Pagination({ page, pages, onPage }: { page: number; pages: number; onPage: (p: number) => void }) {
  if (pages <= 1) return null;
  const nums: (number | "…")[] = [];
  for (let p = 1; p <= pages; p++) {
    if (p === 1 || p === pages || Math.abs(p - page) <= 1) nums.push(p);
    else if (nums[nums.length - 1] !== "…") nums.push("…");
  }
  return (
    <nav aria-label="Pagination" className="mt-6 flex flex-wrap items-center justify-center gap-1">
      <button
        className="inline-flex h-9 items-center gap-1 rounded-lg px-3 text-sm text-ink-soft hover:bg-ice disabled:opacity-40"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
      >
        <ChevronLeft className="h-4 w-4" /> Prev
      </button>
      {nums.map((n, i) =>
        n === "…" ? (
          <span key={`e${i}`} className="px-2 text-mist">…</span>
        ) : (
          <button
            key={n}
            onClick={() => onPage(n)}
            aria-current={n === page ? "page" : undefined}
            className={clsx("h-9 min-w-9 rounded-lg px-2 text-sm", n === page ? "bg-night text-white" : "text-ink-soft hover:bg-ice")}
          >
            {n}
          </button>
        ),
      )}
      <button
        className="inline-flex h-9 items-center gap-1 rounded-lg px-3 text-sm text-ink-soft hover:bg-ice disabled:opacity-40"
        disabled={page >= pages}
        onClick={() => onPage(page + 1)}
      >
        Next <ChevronRight className="h-4 w-4" />
      </button>
    </nav>
  );
}

/* ------------------------------------------------------------------ Modal + Confirm */
export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    ref.current?.focus();
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[90] flex items-end justify-center bg-abyss/50 p-0 backdrop-blur-sm sm:items-center sm:p-4" onClick={onClose}>
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        className={clsx("max-h-[92vh] w-full animate-fade-up overflow-y-auto rounded-t-2xl bg-white shadow-lift outline-none sm:rounded-2xl", wide ? "sm:max-w-4xl" : "sm:max-w-lg")}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-frost bg-white px-5 py-3.5">
          <h2 className="font-display text-lg text-night">{title}</h2>
          <button onClick={onClose} aria-label="Close dialog" className="rounded-lg p-1.5 text-steel hover:bg-ice">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function ConfirmDialog({ open, title, body, confirmLabel = "Confirm", danger, onConfirm, onCancel, loading }: {
  open: boolean; title: string; body: ReactNode; confirmLabel?: string; danger?: boolean; onConfirm: () => void; onCancel: () => void; loading?: boolean;
}) {
  return (
    <Modal open={open} onClose={onCancel} title={title}>
      <div className="text-sm text-ink-soft">{body}</div>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} loading={loading}>{confirmLabel}</Button>
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------ Tabs */
export function Tabs<T extends string>({ tabs, value, onChange, className }: { tabs: { key: T; label: ReactNode }[]; value: T; onChange: (v: T) => void; className?: string }) {
  return (
    <div role="tablist" className={clsx("flex gap-1 overflow-x-auto rounded-xl bg-ice p-1 scrollbar-thin", className)}>
      {tabs.map((t) => (
        <button
          key={t.key}
          role="tab"
          aria-selected={value === t.key}
          onClick={() => onChange(t.key)}
          className={clsx(
            "whitespace-nowrap rounded-lg px-3 py-1.5 text-sm transition-colors",
            value === t.key ? "bg-white font-medium text-night shadow-sm" : "text-ink-soft hover:text-night",
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ Page header */
export function PageHeader({ eyebrow, title, description, actions, children }: { eyebrow?: string; title: string; description?: ReactNode; actions?: ReactNode; children?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-col gap-4 md:mb-8 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        {eyebrow && <p className="mb-1.5 font-mono text-[11px] uppercase tracking-[0.18em] text-cyan-deep">{eyebrow}</p>}
        <h1 className="text-[28px] leading-tight text-night md:text-[34px]">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-ink-soft">{description}</p>}
        {children}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function SectionTitle({ title, action, eyebrow }: { title: string; action?: ReactNode; eyebrow?: string }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-3">
      <div>
        {eyebrow && <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.16em] text-cyan-deep">{eyebrow}</p>}
        <h2 className="text-xl text-night md:text-[22px]">{title}</h2>
      </div>
      {action}
    </div>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-medium text-night">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-steel">{hint}</span>}
    </label>
  );
}

export const inputCls =
  "w-full rounded-lg border border-frost bg-white px-3 py-2 text-sm text-night placeholder:text-mist focus:border-cyan focus:outline-none focus:ring-2 focus:ring-cyan/20";

export function MetaRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-frost/70 py-2.5 last:border-0 sm:flex-row sm:gap-4">
      <dt className="w-36 shrink-0 font-mono text-[11px] uppercase tracking-wide text-steel">{label}</dt>
      <dd className="min-w-0 text-sm text-night">{children}</dd>
    </div>
  );
}
