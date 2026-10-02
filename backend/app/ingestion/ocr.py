"""OCR for scanned PDFs.

    PDF → text extraction (PyMuPDF) → pages with too little text → render page (200 dpi) → tesseract → page text

Uses the `tesseract` command-line program (installed by the Dockerfile: tesseract-ocr). It is called with an
argument list — never through a shell. Page numbers are preserved with the same `[[page N]]` markers as normal text
extraction, so citations can still point at "Page 17".
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings

log = logging.getLogger("polarnexus.ocr")


def available() -> bool:
    return settings.OCR_ENABLED and bool(shutil.which("tesseract"))


def version() -> str | None:
    if not shutil.which("tesseract"):
        return None
    try:
        out = subprocess.run(["tesseract", "--version"], capture_output=True, timeout=10, check=False)
        first = (out.stdout or out.stderr or b"").decode("utf-8", "replace").splitlines()
        return first[0].strip() if first else "tesseract"
    except Exception:
        return "tesseract"


def status() -> dict:
    return {"enabled": settings.OCR_ENABLED, "available": available(), "engine": version(),
            "languages": settings.OCR_LANGUAGES, "min_chars_per_page": settings.OCR_MIN_CHARS_PER_PAGE,
            "max_pages": settings.OCR_MAX_PAGES}


def _lang() -> str:
    langs = [l for l in re.split(r"[+, ]+", settings.OCR_LANGUAGES) if re.fullmatch(r"[a-z_]{3,8}", l)]
    return "+".join(langs) or "eng"


def ocr_page(pdf_page, dpi: int = 200) -> str:
    """Renders one PyMuPDF page and returns tesseract's text for it."""
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "page.png"
        pix = pdf_page.get_pixmap(dpi=dpi)
        pix.save(str(png))
        res = subprocess.run(["tesseract", str(png), "stdout", "-l", _lang(), "--psm", "3"],
                             capture_output=True, timeout=120, check=False)
        if res.returncode != 0:
            raise RuntimeError((res.stderr or b"").decode("utf-8", "replace")[:200] or "tesseract failed")
        return res.stdout.decode("utf-8", "replace")


def extract_pdf_with_ocr(path: Path) -> tuple[str, int, dict, dict]:
    """Returns (text with [[page N]] markers, page count, pdf metadata, ocr report)."""
    import fitz  # PyMuPDF

    report = {"status": "not_needed", "pages_ocr": [], "pages_failed": [], "engine": None, "pages_total": 0}
    parts = []
    with fitz.open(path) as pdf:
        meta = pdf.metadata or {}
        report["pages_total"] = len(pdf)
        need = []
        texts = []
        for i, page in enumerate(pdf, start=1):
            t = re.sub(r"[ \t]+", " ", page.get_text("text")).strip()
            texts.append(t)
            if len(t) < settings.OCR_MIN_CHARS_PER_PAGE:
                need.append(i)
        if need:
            if not available():
                report["status"] = "unavailable"
            else:
                report["engine"] = version()
                for i in need[: settings.OCR_MAX_PAGES]:
                    try:
                        t = re.sub(r"[ \t]+", " ", ocr_page(pdf[i - 1])).strip()
                        if len(t) >= 10:
                            texts[i - 1] = t
                            report["pages_ocr"].append(i)
                        else:
                            report["pages_failed"].append(i)
                    except Exception as exc:
                        log.warning("OCR failed on page %s: %s", i, exc)
                        report["pages_failed"].append(i)
                skipped = need[settings.OCR_MAX_PAGES:]
                report["pages_skipped"] = skipped
                if report["pages_ocr"] and not report["pages_failed"] and not skipped:
                    report["status"] = "applied"
                elif report["pages_ocr"]:
                    report["status"] = "partial"
                else:
                    report["status"] = "failed"
        for i, t in enumerate(texts, start=1):
            if t:
                parts.append(f"[[page {i}]]\n{t}")
    report["pages_needing_ocr"] = need
    return "\n\n".join(parts), report["pages_total"], meta, report
