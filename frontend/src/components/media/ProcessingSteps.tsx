"use client";

import clsx from "clsx";
import { CircleCheck, CircleDashed, CircleMinus, CircleX, LoaderCircle } from "lucide-react";
import type { ProcessingStep } from "@/lib/types";

export const PROCESSING_LABEL: Record<string, string> = {
  uploading: "Uploading",
  processing: "Processing",
  extracting_metadata: "Extracting metadata",
  generating_transcript: "Generating transcript",
  indexing: "Indexing",
  ready: "Ready",
  failed: "Failed",
};

const ICON = { pending: CircleDashed, running: LoaderCircle, done: CircleCheck, skipped: CircleMinus, failed: CircleX };
const COLOR = { pending: "text-mist", running: "text-cyan-deep", done: "text-teal", skipped: "text-steel", failed: "text-coral" };

export function ProcessingStatusPill({ status }: { status: string }) {
  const tone = status === "ready" ? "bg-[#e2f4f1] text-teal" : status === "failed" ? "bg-[#fbe9e5] text-coral" : "bg-[#e3f4fa] text-cyan-deep";
  return (
    <span className={clsx("inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[12px] font-medium", tone)} role="status">
      {status !== "ready" && status !== "failed" && <LoaderCircle className="h-3.5 w-3.5 animate-spin" aria-hidden />}
      {PROCESSING_LABEL[status] || status}
    </span>
  );
}

/** Live view of the media ingestion pipeline. Skipped steps always state why. */
export function ProcessingSteps({ status, steps, error }: { status: string; steps: ProcessingStep[]; error?: string }) {
  return (
    <div>
      <div className="mb-2"><ProcessingStatusPill status={status} /></div>
      <ol className="space-y-1.5">
        {steps.map((s) => {
          const I = ICON[s.status] || CircleDashed;
          return (
            <li key={s.key} className="flex gap-2 text-[13px]">
              <I className={clsx("mt-0.5 h-4 w-4 shrink-0", COLOR[s.status], s.status === "running" && "animate-spin")} aria-hidden />
              <span className="min-w-0">
                <span className={clsx("font-medium", s.status === "pending" ? "text-steel" : "text-night")}>{s.label}</span>
                <span className="sr-only"> — {s.status}</span>
                {s.detail && <span className="block break-words text-[12px] text-steel">{s.detail}</span>}
              </span>
            </li>
          );
        })}
      </ol>
      {error && <p role="alert" className="mt-2 rounded-lg bg-[#fdf6f4] px-3 py-2 text-[12.5px] text-coral">{error}</p>}
    </div>
  );
}
