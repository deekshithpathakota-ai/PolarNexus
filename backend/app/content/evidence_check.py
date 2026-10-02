"""Automated evidence check for generated outreach content.

This is a HEURISTIC check (lexical support matching), designed to flag issues for a human reviewer.
It is not, and does not claim to be, scientific verification.
"""
from __future__ import annotations

import re

from app.utils.text import numbers_in, split_sentences, stems

METHOD_NOTE = ("Automated heuristic check: each sentence is matched against the attached source passages by "
               "shared terms; numbers, citation markers, region names and over-confident wording are also checked. "
               "It flags issues for the reviewer — it is not a scientific verification.")

OVERCLAIM = [r"\bproves?\b", r"\bproven\b", r"\bdefinitely\b", r"\bcertainly\b", r"\bundeniabl", r"\bconclusively\b",
             r"\balways\b", r"\bnever\b", r"\bguarantee", r"\b100\s?%", r"\brevolutionar", r"\bgame.?chang",
             r"\bworld'?s (most|first|best)\b", r"\bwill (cause|destroy|disappear)", r"\bcatastroph", r"\bshocking\b"]
REGION_FAMILIES = {
    "antarctic": ["antarctic", "antarctica", "southern ocean", "dronning maud", "larsemann", "schirmacher", "maitri", "bharati", "prydz"],
    "arctic": ["arctic", "svalbard", "ny-alesund", "ny-ålesund", "kongsfjorden", "himadri", "greenland"],
    "himalaya": ["himalaya", "himalayan", "chandra", "himansh", "third pole"],
}
SKIP_RE = re.compile(r"^(#|source|sources|read more|view in|note to editors|hashtags|words to know|what is this about|"
                     r"what did scientists find|why does it matter|why it matters|what the study found|caveats?)\b", re.I)


def _claim_sentences(body: str) -> list[str]:
    out = []
    for line in body.splitlines():
        line = line.strip().lstrip("-•*0123456789. ").strip()
        line = re.sub(r"\*\*|__|\*", "", line)
        if not line or SKIP_RE.match(line) or line.startswith("#"):
            continue
        for s in split_sentences(line):
            clean = re.sub(r"\[\d+\]", "", s).strip()
            words = re.findall(r"[A-Za-z]{3,}", clean)
            if len(words) < 6 or clean.endswith("?"):
                continue  # headings, hooks, calls-to-action
            if re.search(r"#\w+", clean) and len(re.sub(r"#\w+", "", clean).split()) < 6:
                continue
            out.append(clean)
    return out


def run_evidence_check(body: str, evidence_texts: list[str], citation_count: int) -> dict:
    checks = []
    ev_all = " ".join(evidence_texts)
    ev_stems = [stems(t) for t in evidence_texts]
    ev_lower = ev_all.lower()

    checks.append({"id": "sources_attached", "label": "Sources attached",
                   "status": "pass" if citation_count > 0 else "fail",
                   "detail": f"{citation_count} source passage(s) attached." if citation_count else "No source passages are attached to this draft."})

    bad_markers = sorted({int(n) for n in re.findall(r"\[(\d+)\]", body) if int(n) < 1 or int(n) > citation_count})
    checks.append({"id": "citation_integrity", "label": "Citation markers valid",
                   "status": "fail" if bad_markers else "pass",
                   "detail": (f"Citation marker(s) {', '.join(f'[{n}]' for n in bad_markers)} do not match an attached source."
                              if bad_markers else "Every [n] marker refers to an attached source.")})

    sentence_results = []
    for s in _claim_sentences(body):
        st = stems(s)
        best, best_i = 0.0, None
        for i, es in enumerate(ev_stems):
            if not st:
                continue
            cov = len(st & es) / len(st)
            if cov > best:
                best, best_i = cov, i
        sentence_results.append({"text": s, "support": round(best, 2), "supported": best >= 0.45,
                                 "best_source": (best_i + 1) if best_i is not None else None})
    unsupported = [r for r in sentence_results if not r["supported"]]
    total = len(sentence_results)
    if total == 0:
        status, detail = "warn", "No factual sentences detected to check."
    elif not unsupported:
        status, detail = "pass", f"All {total} factual sentences share substantial wording with the sources."
    elif len(unsupported) / total <= 0.25:
        status, detail = "warn", f"{len(unsupported)} of {total} sentences have weak overlap with the sources — review them."
    else:
        status, detail = "fail", f"{len(unsupported)} of {total} sentences are not clearly supported by the sources."
    checks.append({"id": "claims_supported", "label": "Claims supported by sources", "status": status, "detail": detail})

    ev_numbers = numbers_in(ev_all)
    stray = sorted(n for n in numbers_in(re.sub(r"\[\d+\]", "", body)) if n not in ev_numbers and not re.fullmatch(r"(19|20)\d\d", n))
    checks.append({"id": "numbers", "label": "No unsupported statistics",
                   "status": "warn" if stray else "pass",
                   "detail": f"Number(s) not found in sources: {', '.join(stray)}." if stray else "No numbers outside the sources."})

    hits = sorted({m.group(0) for p in OVERCLAIM for m in re.finditer(p, body, flags=re.I)})
    checks.append({"id": "overclaiming", "label": "No over-confident wording",
                   "status": "warn" if hits else "pass",
                   "detail": f"Review wording: {', '.join(hits)}." if hits else "No over-confident or sensational wording detected."})

    mism = sorted({fam for fam, words in REGION_FAMILIES.items()
                   if any(re.search(rf"\b{w}\b", body, re.I) for w in words) and not any(w in ev_lower for w in words)})
    checks.append({"id": "source_mismatch", "label": "Consistent with source scope",
                   "status": "warn" if mism else "pass",
                   "detail": f"Mentions {', '.join(mism)} which the sources do not discuss." if mism else "Regions mentioned match the sources."})

    overall = "fail" if any(c["status"] == "fail" for c in checks) else "warn" if any(c["status"] == "warn" for c in checks) else "pass"
    return {"overall": overall, "checks": checks, "sentences": sentence_results, "method_note": METHOD_NOTE}
