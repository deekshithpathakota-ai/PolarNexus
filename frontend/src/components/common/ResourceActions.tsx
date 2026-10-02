"use client";

import { Bookmark, BookmarkCheck, Check, Copy, Download, Quote, Share2 } from "lucide-react";
import { useState } from "react";
import { useToast } from "./Toast";
import { Button, Modal } from "./ui";
import { downloadUrl, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Save / Share / Cite / Download actions shared by every detail page. */
export function ResourceActions({ itemType, slug, label, citation, download }: {
  itemType: "document" | "dataset" | "media" | "expedition" | "station" | "researcher";
  slug: string;
  label: string;
  citation?: string;
  download?: string;
}) {
  const { user } = useAuth();
  const toast = useToast();
  const [saved, setSaved] = useState(false);
  const [share, setShare] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const url = typeof window !== "undefined" ? window.location.href.split("?")[0] : "";

  const copy = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(null), 1600);
    } catch {
      toast("error", "Clipboard unavailable", "Select and copy the text manually.");
    }
  };

  return (
    <>
      <Button
        variant="secondary"
        size="sm"
        icon={saved ? <BookmarkCheck className="h-3.5 w-3.5 text-teal" /> : <Bookmark className="h-3.5 w-3.5" />}
        onClick={async () => {
          if (!user) return toast("info", "Sign in to save resources", "Saved items appear in My Knowledge.");
          try {
            await post("/api/saved", { item_type: itemType, item_slug: slug, label });
            setSaved(true);
            toast("success", "Saved to My Knowledge");
          } catch (e) {
            toast("error", "Could not save", (e as Error).message);
          }
        }}
      >
        {saved ? "Saved" : "Save"}
      </Button>
      <Button variant="secondary" size="sm" icon={<Share2 className="h-3.5 w-3.5" />} onClick={() => setShare(true)}>
        Share
      </Button>
      {download && (
        <a href={downloadUrl(download)} className="inline-flex h-8 items-center gap-2 rounded-lg border border-frost bg-white px-3 text-[13px] font-medium text-night hover:bg-ice" download>
          <Download className="h-3.5 w-3.5" /> Download
        </a>
      )}
      <Modal open={share} onClose={() => setShare(false)} title="Share & cite">
        <p className="mb-1.5 text-[13px] font-medium text-night">Link</p>
        <div className="flex gap-2">
          <input readOnly value={url} className="min-w-0 flex-1 rounded-lg border border-frost bg-snow px-3 py-2 font-mono text-[12px]" aria-label="Resource link" />
          <Button size="sm" variant="secondary" onClick={() => copy(url, "link")} icon={copied === "link" ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}>
            {copied === "link" ? "Copied" : "Copy"}
          </Button>
        </div>
        {citation && (
          <>
            <p className="mb-1.5 mt-4 flex items-center gap-1.5 text-[13px] font-medium text-night"><Quote className="h-3.5 w-3.5" /> Citation</p>
            <p className="rounded-lg border border-frost bg-snow p-3 text-[13px] leading-relaxed text-ink-soft">{citation}</p>
            <Button size="sm" variant="secondary" className="mt-2" onClick={() => copy(citation, "cite")} icon={copied === "cite" ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}>
              {copied === "cite" ? "Copied" : "Copy citation"}
            </Button>
          </>
        )}
        {typeof navigator !== "undefined" && "share" in navigator && (
          <Button size="sm" className="mt-4 w-full" onClick={() => navigator.share({ title: label, url }).catch(() => {})} icon={<Share2 className="h-3.5 w-3.5" />}>
            Share via device…
          </Button>
        )}
        <p className="mt-4 text-[12px] text-steel">Only public records are shareable. Internal records require a signed-in professional account.</p>
      </Modal>
    </>
  );
}
