"""Scientific dataset ingestion (CSV / JSON).

    Upload → file validation → format detection → schema detection → column type inference → preview
    → validation (missing values, duplicates, invalid numbers / dates / coordinates, inconsistent types)
    → metadata → user confirmation → dataset registration → indexing → visualisation

Parsers are registered by extension in `PARSERS`; each returns (columns, rows as list[dict[str, str]]).
NetCDF/HDF5 can be added later by registering a parser that flattens variables into the same row shape
(e.g. with xarray) — the analysis, validation and registration steps below do not change.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import math
import re
import statistics
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Dataset, DatasetRecord, DatasetUpload, ResourceTopic, Topic, User
from app.services.audit import audit, notify
from app.utils.text import slugify

log = logging.getLogger("polarnexus.datasets")

MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "-", "--", "nd"}
FILL_VALUES = {"-9999", "-999", "-99.99", "-999.9", "9999", "-9999.0", "-999.0", "99999"}
LAT_NAMES = {"lat", "latitude", "lat_deg", "latitude_deg", "y_lat"}
LON_NAMES = {"lon", "long", "lng", "longitude", "lon_deg", "longitude_deg", "x_lon"}
TIME_NAMES = {"date", "datetime", "time", "timestamp", "observed_at", "date_time", "obs_time", "sampling_date"}
YEAR_NAMES = {"year", "yr"}
MONTH_NAMES = {"month", "mo", "mon"}
DAY_NAMES = {"day", "dd"}
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m", "%Y%m%d", "%d.%m.%Y"]
REGIONS = {"Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India", "Global"}

REGISTER_STEPS = [("register", "Register dataset"), ("records", "Store records"), ("metadata", "Scientific metadata"),
                  ("index", "Index for search"), ("provenance", "Provenance & version"), ("ready", "Ready to explore")]


class DatasetValidationError(ValueError):
    pass


# ------------------------------------------------------------------ parsing
def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise DatasetValidationError("The file must be UTF-8 encoded text.")


def parse_csv(data: bytes) -> tuple[list[str], list[dict[str, str]], dict]:
    text = _decode(data)
    if "\x00" in text[:4096]:
        raise DatasetValidationError("The file contains binary content — not a CSV file.")
    lines = text.splitlines()
    comments = [l for l in lines[:50] if l.lstrip().startswith("#")]
    body = "\n".join(l for l in lines if l.strip() and not l.lstrip().startswith("#"))
    if not body.strip():
        raise DatasetValidationError("The CSV file has no data rows.")
    sample = body[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delim = dialect.delimiter
    except csv.Error:
        delim = ","
    reader = csv.reader(io.StringIO(body), delimiter=delim)
    try:
        header = [h.strip() for h in next(reader)]
    except StopIteration:
        raise DatasetValidationError("The CSV file is empty.")
    if not header or all(not h for h in header):
        raise DatasetValidationError("The first row must contain column names.")
    seen: Counter = Counter()
    cols = []
    for i, h in enumerate(header):
        name = h or f"column_{i + 1}"
        seen[name] += 1
        cols.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    rows, ragged = [], 0
    for raw in reader:
        if not any(c.strip() for c in raw):
            continue
        if len(raw) != len(cols):
            ragged += 1
        rows.append({c: (raw[i].strip() if i < len(raw) else "") for i, c in enumerate(cols)})
        if len(rows) > settings.MAX_DATASET_ROWS:
            raise DatasetValidationError(f"The file has more than {settings.MAX_DATASET_ROWS:,} rows — split it or raise MAX_DATASET_ROWS.")
    return cols, rows, {"delimiter": delim, "comment_lines": comments[:10], "ragged_rows": ragged}


def _flatten(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)[:500]
    return str(v).strip()


def parse_json(data: bytes) -> tuple[list[str], list[dict[str, str]], dict]:
    try:
        obj = json.loads(_decode(data))
    except json.JSONDecodeError as exc:
        raise DatasetValidationError(f"Invalid JSON: {exc.msg} (line {exc.lineno}).")
    shape = "array"
    records = None
    if isinstance(obj, dict) and obj.get("type") == "FeatureCollection" and isinstance(obj.get("features"), list):
        shape = "geojson"
        records = []
        for f in obj["features"]:
            props = dict((f or {}).get("properties") or {})
            geom = (f or {}).get("geometry") or {}
            if geom.get("type") == "Point" and isinstance(geom.get("coordinates"), list) and len(geom["coordinates"]) >= 2:
                props.setdefault("longitude", geom["coordinates"][0])
                props.setdefault("latitude", geom["coordinates"][1])
            records.append(props)
    elif isinstance(obj, list):
        records = obj
    elif isinstance(obj, dict):
        for key in ("data", "records", "rows", "items", "observations", "results"):
            if isinstance(obj.get(key), list):
                records, shape = obj[key], f"object.{key}"
                break
        if records is None:
            lists = [k for k, v in obj.items() if isinstance(v, list) and v and isinstance(v[0], dict)]
            if lists:
                records, shape = obj[lists[0]], f"object.{lists[0]}"
    if not records:
        raise DatasetValidationError("JSON must be an array of records, an object with a 'data'/'records' array, or GeoJSON.")
    if not all(isinstance(r, dict) for r in records):
        raise DatasetValidationError("Every JSON record must be an object (key → value).")
    if len(records) > settings.MAX_DATASET_ROWS:
        raise DatasetValidationError(f"The file has more than {settings.MAX_DATASET_ROWS:,} records.")
    cols: list[str] = []
    for r in records:
        for k in r:
            if str(k) not in cols:
                cols.append(str(k))
    rows = [{c: _flatten(r.get(c)) for c in cols} for r in records]
    return cols, rows, {"json_shape": shape}


# NetCDF (".nc") would be registered here later, flattening each variable to columns.
PARSERS = {".csv": parse_csv, ".tsv": parse_csv, ".json": parse_json, ".geojson": parse_json}


def detect_format(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in PARSERS:
        raise DatasetValidationError(f"Unsupported dataset format '{ext or 'none'}'. Supported: CSV, TSV, JSON, GeoJSON. "
                                     "(NetCDF support is planned.)")
    head = data[:64].lstrip()
    if ext in {".json", ".geojson"} and head[:1] not in (b"{", b"["):
        raise DatasetValidationError("The file does not look like JSON (it must start with '{' or '[').")
    if ext in {".csv", ".tsv"} and head[:1] in (b"{", b"["):
        raise DatasetValidationError("The file looks like JSON but has a .csv extension.")
    if data[:4] in (b"\x89HDF", b"CDF\x01", b"CDF\x02") or data[:2] == b"PK":
        raise DatasetValidationError("Binary file detected — only text CSV/JSON is accepted.")
    return ext


# ------------------------------------------------------------------ type inference
def _num(s: str) -> float | None:
    try:
        v = float(s.replace(",", "")) if re.fullmatch(r"[-+]?\d{1,3}(,\d{3})+(\.\d+)?", s) else float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def _date(s: str) -> datetime | None:
    s = s.strip()
    if not s or len(s) < 6:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d.replace(tzinfo=None) if d.tzinfo else d
    except ValueError:
        pass
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f)
        except ValueError:
            continue
    return None


def _is_missing(s: str) -> bool:
    return s.strip().lower() in MISSING_TOKENS


def infer_column(name: str, values: list[str]) -> dict:
    present = [v for v in values if not _is_missing(v)]
    n = len(values)
    missing = n - len(present)
    low = name.strip().lower()
    info: dict = {"name": name, "missing": missing, "missing_pct": round(missing / n * 100, 1) if n else 0,
                  "unique": len(set(present)), "examples": list(dict.fromkeys(present))[:4]}
    if not present:
        info.update(type="empty", role="")
        return info
    nums = [_num(v) for v in present]
    num_ok = [x for x in nums if x is not None]
    num_ratio = len(num_ok) / len(present)
    dates = [_date(v) for v in present] if num_ratio < 0.9 or low in TIME_NAMES else []
    date_ok = [d for d in dates if d is not None]
    date_ratio = len(date_ok) / len(present) if dates else 0.0
    bools = {v.lower() for v in present} <= {"true", "false", "yes", "no", "0", "1", "y", "n"}
    if num_ratio >= 0.7 and not (low in TIME_NAMES and date_ratio > num_ratio):
        integer = all(float(x).is_integer() for x in num_ok)
        info.update(type="integer" if integer else "number", invalid=len(present) - len(num_ok))
        info["invalid_examples"] = [v for v, x in zip(present, nums) if x is None][:3]
        info["stats"] = {"min": min(num_ok), "max": max(num_ok), "mean": round(statistics.fmean(num_ok), 4),
                         "std": round(statistics.pstdev(num_ok), 4) if len(num_ok) > 1 else 0.0, "count": len(num_ok)}
        info["fill_values"] = sorted({v for v in present if v in FILL_VALUES})
    elif date_ratio >= 0.7:
        kind = "datetime" if any(d.hour or d.minute for d in date_ok) else "date"
        info.update(type=kind, invalid=len(present) - len(date_ok))
        info["invalid_examples"] = [v for v, d in zip(present, dates) if d is None][:3]
        n = 19 if kind == "datetime" else 10
        info["stats"] = {"min": min(date_ok).isoformat()[:n], "max": max(date_ok).isoformat()[:n], "count": len(date_ok)}
    elif bools and len(present) > 1:
        info.update(type="boolean", invalid=0)
    else:
        info.update(type="category" if info["unique"] <= max(12, len(present) // 20) else "text", invalid=0)
        if 0.3 <= num_ratio < 0.7:
            info["mixed"] = round(num_ratio * 100)
    role = ""
    if low in LAT_NAMES and info["type"] in {"number", "integer"}:
        role = "latitude"
    elif low in LON_NAMES and info["type"] in {"number", "integer"}:
        role = "longitude"
    elif low in TIME_NAMES and info["type"] in {"date", "datetime"}:
        role = "time"
    elif info["type"] in {"date", "datetime"}:
        role = "time"
    elif low in YEAR_NAMES and info["type"] == "integer" and 1500 <= info["stats"]["min"] and info["stats"]["max"] <= 2200:
        role = "year"
    elif low in MONTH_NAMES and info["type"] == "integer" and 1 <= info["stats"]["min"] and info["stats"]["max"] <= 12:
        role = "month"
    elif low in DAY_NAMES and info["type"] == "integer" and 1 <= info["stats"]["min"] and info["stats"]["max"] <= 31:
        role = "day"
    info["role"] = role
    return info


def analyze(filename: str, data: bytes) -> dict:
    t0 = time.perf_counter()
    if not data:
        raise DatasetValidationError("The file is empty.")
    if len(data) > settings.MAX_DATASET_MB * 1024 * 1024:
        raise DatasetValidationError(f"The file exceeds the {settings.MAX_DATASET_MB} MB limit.")
    ext = detect_format(filename, data)
    cols, rows, fmt_info = PARSERS[ext](data)
    if not rows:
        raise DatasetValidationError("No data rows were found.")
    columns = [infer_column(c, [r[c] for r in rows]) for c in cols]
    by_role = {c["role"]: c["name"] for c in columns if c["role"]}
    issues: list[dict] = []

    def issue(sev, code, msg, column=None, count=None, examples=None):
        issues.append({"severity": sev, "code": code, "message": msg, "column": column, "count": count,
                       "examples": examples or []})

    # missing values
    for c in columns:
        if c["type"] == "empty":
            issue("warning", "empty_column", f"Column '{c['name']}' has no values.", c["name"], len(rows))
        elif c["missing"]:
            issue("warning" if c["missing_pct"] >= 20 else "info", "missing_values",
                  f"{c['missing']:,} missing value(s) in '{c['name']}' ({c['missing_pct']}%).", c["name"], c["missing"])
        if c.get("invalid"):
            kind = "numeric" if c["type"] in {"number", "integer"} else "date"
            issue("error" if c["invalid"] / max(1, len(rows) - c["missing"]) > 0.05 else "warning",
                  f"invalid_{kind}", f"{c['invalid']:,} value(s) in '{c['name']}' are not valid {kind} values.",
                  c["name"], c["invalid"], c.get("invalid_examples"))
        if c.get("mixed"):
            issue("warning", "inconsistent_types", f"'{c['name']}' mixes numbers ({c['mixed']}%) and text — stored as text.",
                  c["name"])
        if c.get("fill_values"):
            issue("warning", "fill_values", f"'{c['name']}' contains common fill values ({', '.join(c['fill_values'])}) "
                  "that may stand for missing data. They are kept as numbers unless you remove them.", c["name"])
    # duplicates
    dup = sum(n - 1 for n in Counter(tuple(r[c] for c in cols) for r in rows).values() if n > 1)
    if dup:
        issue("warning", "duplicate_rows", f"{dup:,} duplicate row(s) (identical in every column).", None, dup)
    if fmt_info.get("ragged_rows"):
        issue("warning", "ragged_rows", f"{fmt_info['ragged_rows']:,} row(s) have a different number of fields than the header.",
              None, fmt_info["ragged_rows"])
    # coordinates
    bbox = None
    if "latitude" in by_role and "longitude" in by_role:
        bad, lats, lons = [], [], []
        for i, r in enumerate(rows):
            la, lo = _num(r[by_role["latitude"]]), _num(r[by_role["longitude"]])
            if la is None or lo is None:
                continue
            if not (-90 <= la <= 90) or not (-180 <= lo <= 360):
                bad.append(f"row {i + 2}: {la}, {lo}")
            else:
                lats.append(la)
                lons.append(lo if lo <= 180 else lo - 360)
        if bad:
            issue("error", "invalid_coordinates", f"{len(bad):,} row(s) have coordinates outside valid ranges.",
                  by_role["latitude"], len(bad), bad[:3])
        if lats:
            bbox = {"min_lat": min(lats), "max_lat": max(lats), "min_lon": min(lons), "max_lon": max(lons)}
    elif "latitude" in by_role or "longitude" in by_role:
        issue("info", "partial_coordinates", "Only one coordinate column was recognised; records will not be mapped.")
    # time
    time_mode, t_min, t_max = None, None, None
    if "time" in by_role:
        time_mode = by_role["time"]
        st = next(c for c in columns if c["name"] == by_role["time"]).get("stats") or {}
        t_min, t_max = st.get("min"), st.get("max")
    elif "year" in by_role:
        time_mode = "+".join(x for x in (by_role.get("year"), by_role.get("month"), by_role.get("day")) if x)
        times = [_compose_time(r, by_role) for r in rows]
        times = [t for t in times if t]
        if times:
            t_min, t_max = min(times).isoformat()[:10], max(times).isoformat()[:10]
    numeric = [c["name"] for c in columns if c["type"] in {"number", "integer"} and not c["role"]]
    suggest_region = None
    if bbox:
        mid = (bbox["min_lat"] + bbox["max_lat"]) / 2
        suggest_region = "Antarctic" if mid <= -60 else "Southern Ocean" if mid <= -40 else "Arctic" if mid >= 60 else None
    charts = []
    if numeric and time_mode:
        charts.append("time_series")
    if bbox:
        charts.append("map")
    if len(numeric) >= 2:
        charts.append("scatter")
    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    return {
        "filename": filename, "format": ext.lstrip(".").upper(), "format_detail": fmt_info,
        "rows": len(rows), "columns": len(cols), "schema": columns, "roles": by_role,
        "preview": rows[:20], "issues": issues, "duplicate_rows": dup, "duplicates": [],
        "summary": {"errors": errors, "warnings": warnings,
                    "verdict": "fail" if errors else "warn" if warnings else "pass"},
        "temporal": {"column": time_mode, "start": t_min, "end": t_max},
        "spatial": {"bbox": bbox, "suggested_region": suggest_region},
        "numeric_variables": numeric, "suggested_charts": charts,
        "suggested_title": re.sub(r"[_-]+", " ", Path(filename).stem).strip().title()[:200],
        "took_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def _compose_time(r: dict, roles: dict) -> datetime | None:
    if roles.get("time"):
        return _date(r[roles["time"]])
    y = _num(r.get(roles.get("year", ""), "") or "")
    if y is None:
        return None
    m = _num(r.get(roles.get("month", ""), "") or "") if roles.get("month") else 1
    d = _num(r.get(roles.get("day", ""), "") or "") if roles.get("day") else 1
    try:
        return datetime(int(y), int(m or 1), int(d or 1))
    except (ValueError, TypeError):
        return None


# ------------------------------------------------------------------ registration
def _typed(value: str, ctype: str):
    if _is_missing(value):
        return None
    if ctype == "integer":
        x = _num(value)
        return int(x) if x is not None else value
    if ctype == "number":
        x = _num(value)
        return x if x is not None else value
    if ctype == "boolean":
        return value.lower() in {"true", "yes", "1", "y"}
    return value


def build_records(rows: list[dict], schema: list[dict], roles: dict, drop_duplicates: bool) -> tuple[list[dict], int]:
    types = {c["name"]: c["type"] for c in schema}
    seen, out, dropped = set(), [], 0
    for r in rows:
        if drop_duplicates:
            key = tuple(r.values())
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
        lat = _num(r[roles["latitude"]]) if roles.get("latitude") else None
        lon = _num(r[roles["longitude"]]) if roles.get("longitude") else None
        if lat is not None and not -90 <= lat <= 90:
            lat = None
        if lon is not None:
            lon = lon - 360 if 180 < lon <= 360 else lon
            if not -180 <= lon <= 180:
                lon = None
        values = {k: _typed(v, types.get(k, "text")) for k, v in r.items()
                  if k not in {roles.get("latitude"), roles.get("longitude")}}
        out.append({"observed_at": _compose_time(r, roles), "latitude": lat if lon is not None else None,
                    "longitude": lon if lat is not None else None, "values": values})
    return out, dropped


def variables_for(schema: list[dict], roles: dict, units: dict[str, str], descriptions: dict[str, str]) -> list[dict]:
    role_cols = {v: k for k, v in roles.items()}
    out = []
    for c in schema:
        if role_cols.get(c["name"]) in {"latitude", "longitude"}:
            continue
        role = role_cols.get(c["name"])
        if role in {"year", "month", "day"}:
            unit = "time component"
        elif role == "time" or c["type"] in {"date", "datetime"}:
            unit = "ISO date" if c["type"] == "date" else "ISO datetime"
        elif c["type"] in {"number", "integer"}:
            unit = (units.get(c["name"]) or "").strip()[:40] or "unitless (not specified)"
        else:
            unit = "category" if c["type"] in {"category", "boolean"} else "text"
        out.append({"name": c["name"], "unit": unit,
                    "description": (descriptions.get(c["name"]) or "").strip()[:300] or f"{c['type']} column"})
    return out


def register(upload_id: int, meta: dict, user_id: int, provenance: dict | None = None) -> int | None:
    """Creates the Dataset + records from a confirmed staged upload. Runs in a background task (own session)."""
    from app.rag.indexer import index_resource
    from app.services import provenance as prov
    from app.services import versions
    from app.services.storage import get_storage

    db = SessionLocal()
    up = db.get(DatasetUpload, upload_id)
    user = db.get(User, user_id) if user_id else None
    ds_id = None

    def step(key, status, detail=""):
        steps = [dict(s) for s in (up.steps or [])]
        for s in steps:
            if s["key"] == key:
                s["status"], s["detail"] = status, detail[:300]
        up.steps = steps
        db.commit()

    try:
        a = up.analysis
        step("register", "running")
        path = get_storage().local_path(up.file_key)
        data = path.read_bytes()
        ext = Path(up.filename).suffix.lower()
        cols, rows, _ = PARSERS[ext](data)
        schema, roles = a["schema"], a["roles"]
        records, dropped = build_records(rows, schema, roles, bool(meta.get("drop_duplicates")))
        times = [r["observed_at"] for r in records if r["observed_at"]]
        slug = slugify(meta.get("slug") or meta["title"])[:150] or f"dataset-{up.id}"
        if db.scalar(select(Dataset).where(Dataset.slug == slug)):
            slug = f"{slug}-{up.id}"
        bbox = (a.get("spatial") or {}).get("bbox")
        spatial = meta.get("spatial_coverage") or (
            f"lat {bbox['min_lat']:.2f}…{bbox['max_lat']:.2f}, lon {bbox['min_lon']:.2f}…{bbox['max_lon']:.2f}" if bbox else "")
        ds = Dataset(
            slug=slug, title=meta["title"][:300], description=meta.get("description") or "",
            region=meta.get("region") or "Global",
            data_type="Time series" if times and a["numeric_variables"] else "Point observations" if bbox else "Tabular",
            temporal_start=min(times).date() if times else None, temporal_end=max(times).date() if times else None,
            spatial_coverage=spatial[:255], variables=variables_for(schema, roles, meta.get("units") or {}, meta.get("descriptions") or {}),
            source=(meta.get("source") or (f"Uploaded by {user.name}" if user else "Upload"))[:255],
            format=a["format"], license=(meta.get("license") or "")[:64],
            size_label=f"{up.size_bytes / 1024:.0f} KB" if up.size_bytes < 1024 * 1024 else f"{up.size_bytes / 1048576:.1f} MB",
            record_count=len(records), year=(max(times).year if times else int(meta.get("year") or datetime.now().year)),
            keywords=[k for k in (meta.get("keywords") or []) if k][:12], visibility=meta.get("visibility") or "public",
            status="processing", is_demo=False, doi=(meta.get("doi") or "")[:160], creator=(meta.get("creator") or "")[:255],
            source_url=(meta.get("source_url") or "")[:500], content_hash=up.content_hash, file_path=str(path),
            columns_schema=[{k: c.get(k) for k in ("name", "type", "role", "missing", "unique", "stats")} for c in schema],
            quality_report={"issues": a["issues"], "summary": a["summary"], "duplicates_dropped": dropped,
                            "rows_in_file": a["rows"], "time_derivation": (a.get("temporal") or {}).get("column")},
            uploaded_by=user.id if user else None)
        db.add(ds)
        db.flush()
        ds_id = ds.id
        up.dataset_id = ds.id
        step("register", "done", f"{ds.title} ({a['format']}, {len(schema)} columns)")
        step("records", "running")
        batch = []
        for r in records:
            batch.append(DatasetRecord(dataset_id=ds.id, observed_at=r["observed_at"], latitude=r["latitude"],
                                       longitude=r["longitude"], values=r["values"]))
            if len(batch) >= 2000:
                db.add_all(batch)
                db.flush()
                batch = []
        db.add_all(batch)
        db.commit()
        step("records", "done", f"{len(records):,} records" + (f" ({dropped} duplicate rows dropped)" if dropped else ""))
        for tslug in meta.get("topics") or []:
            t = db.scalar(select(Topic).where(Topic.slug == tslug))
            if t:
                db.add(ResourceTopic(resource_type="dataset", resource_id=ds.id, topic_id=t.id))
        db.commit()
        step("metadata", "done", ", ".join(x for x in (
            f"temporal {ds.temporal_start}…{ds.temporal_end}" if ds.temporal_start else "",
            "georeferenced" if bbox else "", f"DOI {ds.doi}" if ds.doi else "no DOI supplied") if x))
        step("index", "running")
        index_resource(db, "dataset", ds.id)
        step("index", "done", "Description and variables indexed (keyword + semantic)")
        p = prov.ensure_for(db, "dataset", ds, commit=False)
        if provenance:
            for k, v in provenance.items():
                setattr(p, k, v)
        else:
            p.source_type, p.verification_status = "Researcher upload", "user_uploaded"
            p.source_organisation = meta.get("creator") or (user.institution if user else "")
            p.source_url, p.license = ds.source_url, ds.license
            p.data_quality = f"Validation: {a['summary']['verdict']} ({a['summary']['errors']} errors, {a['summary']['warnings']} warnings)"
            p.provenance_notes = "Uploaded through the dataset ingestion pipeline. Awaiting administrator verification."
        p.imported_at = datetime.now(timezone.utc)
        versions.record(db, "dataset", ds, f"Imported from {up.filename}", p.verification_status, user,
                        user_name="Seed import" if not user else "", commit=False)
        ds.status = "indexed"
        up.status = "registered"
        db.commit()
        step("provenance", "done", prov.VERIFICATION.get(p.verification_status, ("",))[0] + " · version 1")
        step("ready", "done", "Ready to explore")
        if user:
            audit(db, user, "upload", "dataset", ds.slug, f"Registered {up.filename}: {len(records)} records")
            notify(db, "Dataset registered", f"“{ds.title}” is ready to explore.", f"/datasets/{ds.slug}", "success", user_id=user.id)
        return ds.id
    except Exception as exc:
        log.exception("dataset registration failed")
        db.rollback()
        up = db.get(DatasetUpload, upload_id)
        steps = [dict(s) for s in (up.steps or [])]
        for s in steps:
            if s["status"] in {"running", "pending"}:
                s["status"] = "failed" if s["status"] == "running" else "skipped"
        up.steps, up.status = steps, "failed"
        up.error = str(exc) if isinstance(exc, DatasetValidationError) else "Registration failed. Check the file and try again."
        if ds_id:
            d = db.get(Dataset, ds_id)
            if d:
                d.status = "failed"
        db.commit()
        if user:
            audit(db, user, "upload", "dataset", up.filename[:64], up.error, status="failure")
        return None
    finally:
        db.close()


def initial_register_steps() -> list[dict]:
    return [{"key": k, "label": l, "status": "pending", "detail": ""} for k, l in REGISTER_STEPS]


def parse_date_param(v: str | None) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise DatasetValidationError("Dates must be YYYY-MM-DD.")
