export const BRAND = process.env.NEXT_PUBLIC_BRAND_NAME || "PolarNexus";
export const TAGLINE = "From Polar Research to Public Understanding.";

export function fmtDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" }) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", opts);
}

export function timeAgo(iso: string | null | undefined) {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 86400 * 30) return `${Math.floor(diff / 86400)} d ago`;
  return fmtDate(iso);
}

export function fmtNum(n: number | null | undefined) {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("en-IN");
}

export function coord(lat: number, lon: number) {
  const la = `${Math.abs(lat).toFixed(2)}°${lat < 0 ? "S" : "N"}`;
  const lo = `${Math.abs(lon).toFixed(2)}°${lon < 0 ? "W" : "E"}`;
  return `${la}, ${lo}`;
}

export const STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  under_review: "Under Review",
  changes_requested: "Changes Requested",
  approved: "Approved",
  published: "Published",
  rejected: "Rejected",
};

export const FORMAT_LABEL: Record<string, string> = {
  website: "Website · Research highlight",
  linkedin: "LinkedIn · Professional post",
  instagram: "Instagram · Educational caption",
  student: "Student · Simple explanation",
  public: "Public · Plain language",
  media: "Media · Press-style summary",
};

export const MODE_LABEL: Record<string, string> = {
  llm: "LLM",
  template: "Template",
  curated_demo: "Demo (curated)",
  manual: "Manual",
  extractive: "Extractive",
};

export function genModeLabel(mode: string) {
  const base = mode.replace("+edited", "");
  return (MODE_LABEL[base] || base) + (mode.includes("+edited") ? " · edited" : "");
}

export function plural(n: number, word: string, pluralWord?: string) {
  return `${fmtNum(n)} ${n === 1 ? word : pluralWord || word + "s"}`;
}

export function hashString(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
