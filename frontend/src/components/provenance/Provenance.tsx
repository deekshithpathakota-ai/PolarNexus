"use client";

import clsx from "clsx";
import { BadgeCheck, Clock, ExternalLink, FlaskConical, Fingerprint, Globe, Handshake, Landmark, ShieldQuestion, Upload } from "lucide-react";
import type { ReactNode } from "react";
import { Card, InfoTip } from "@/components/common/ui";
import { fmtDate } from "@/lib/format";
import type { Provenance, VerificationStatus } from "@/lib/types";

const STYLE: Record<VerificationStatus, { cls: string; icon: typeof BadgeCheck; label: string }> = {
  verified: { cls: "border-[#bfe5df] bg-[#e2f4f1] text-teal", icon: BadgeCheck, label: "Verified" },
  public_source: { cls: "border-[#b9d9ea] bg-[#eaf5fb] text-[#0d6b8a]", icon: Globe, label: "Public source" },
  partner_source: { cls: "border-[#c2e6f2] bg-[#e3f4fa] text-cyan-deep", icon: Handshake, label: "Partner source" },
  user_uploaded: { cls: "border-[#dcd7f5] bg-[#efedfb] text-[#5a4bb5]", icon: Upload, label: "User uploaded" },
  pending_review: { cls: "border-[#f0dcb4] bg-[#fbf1df] text-[#8a5c0c]", icon: Clock, label: "Pending review" },
  demo_data: { cls: "border-dashed border-[#e2c58f] bg-[#fdf8ee] text-[#8a5c0c]", icon: FlaskConical, label: "Demo data" },
  synthetic_demo: { cls: "border-dashed border-[#f2cfc6] bg-[#fdf6f4] text-coral", icon: FlaskConical, label: "Synthetic" },
  unverified: { cls: "border-frost bg-ice text-ink-soft", icon: ShieldQuestion, label: "Unverified" },
};

/** Compact verification label used on cards, search results, map popups and timelines. */
export function VerificationBadge({ status, label, official, className }: {
  status?: VerificationStatus | string | null; label?: string; official?: boolean; className?: string;
}) {
  const s = STYLE[(status as VerificationStatus) || "unverified"] || STYLE.unverified;
  const I = official ? Landmark : s.icon;
  return (
    <span
      title={official ? "Verified against official public information" : label || s.label}
      className={clsx("inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-wide", s.cls, className)}
    >
      <I className="h-3 w-3" aria-hidden />
      {official ? "Official · verified" : label || s.label}
    </span>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  if (children === null || children === undefined || children === "" || children === false) return null;
  return (
    <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-3 border-b border-frost/70 py-2 text-[13px] last:border-0">
      <dt className="font-mono text-[10.5px] uppercase tracking-wide text-steel">{label}</dt>
      <dd className="min-w-0 break-words text-night">{children}</dd>
    </div>
  );
}

/** "Data Provenance" section shown on every resource detail page. */
export function ProvenancePanel({ p, compact }: { p?: Provenance | null; compact?: boolean }) {
  if (!p) return null;
  return (
    <Card as="section" aria-labelledby="provenance-heading" className="p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id="provenance-heading" className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-steel">
          <Fingerprint className="h-4 w-4 text-cyan-deep" aria-hidden /> Data Provenance
          <InfoTip label="Provenance" text="Where this record came from, under what licence, and how far it has been verified. Demonstration and synthetic records are always labelled." />
        </h2>
        <VerificationBadge status={p.verification_status} label={p.verification_label} official={p.official} />
      </div>
      {p.notice && (
        <div role="note" className={clsx("mb-3 rounded-lg border px-3 py-2 text-[12.5px] leading-relaxed",
          p.verification_status === "synthetic_demo" ? "border-[#f2cfc6] bg-[#fdf6f4] text-[#8f3b28]" : "border-[#f0dcb4] bg-[#fdf8ee] text-[#7a520b]")}>
          <strong className="mb-0.5 block font-mono text-[10.5px] uppercase tracking-wider">
            {p.verification_status === "synthetic_demo" ? "Synthetic demonstration" : "Demo data"}
          </strong>
          {p.notice}
        </div>
      )}
      <dl>
        <Row label="Source org.">{p.source_organisation}</Row>
        <Row label="Source type">{p.source_type}</Row>
        <Row label="Verification">
          <span>{p.verification_label}</span>
          {!compact && <span className="block text-[12px] text-steel">{p.verification_description}</span>}
        </Row>
        {p.source_url && (
          <Row label="Original">
            <a href={p.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-cyan-deep hover:underline">
              View source <ExternalLink className="h-3 w-3" />
            </a>
          </Row>
        )}
        {!compact && <Row label="Identifier"><span className="font-mono text-[12px]">{p.original_identifier}</span></Row>}
        <Row label="Licence">{p.license}</Row>
        <Row label="Data quality">{p.data_quality}</Row>
        {p.publication_date && <Row label="Published">{fmtDate(p.publication_date)}</Row>}
        {p.collection_date && <Row label="Collected">{fmtDate(p.collection_date)}</Row>}
        {p.imported_at && <Row label="Imported">{fmtDate(p.imported_at)}</Row>}
        <Row label="Last verified">{p.last_verified_at ? `${fmtDate(p.last_verified_at)}${p.verified_by ? ` · ${p.verified_by}` : ""}` : p.verified_by || "Not yet verified"}</Row>
        {p.provenance_notes && !compact && <Row label="Notes"><span className="text-ink-soft">{p.provenance_notes}</span></Row>}
      </dl>
    </Card>
  );
}
