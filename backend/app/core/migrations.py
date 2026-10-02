"""Additive, idempotent schema migrations.

The prototype creates tables with `Base.metadata.create_all`, which never alters existing tables. This module
brings an *existing* database up to date without touching its data:

* new tables are created by `create_all` (called before `migrate`),
* new columns are added with `ALTER TABLE … ADD COLUMN` (nullable, or with the column's server default),
* data backfills run once and are recorded in `schema_migrations`.

Nothing is ever dropped or renamed. Safe to run on every start-up, on SQLite and PostgreSQL.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.database import Base

log = logging.getLogger("polarnexus.migrations")

SCHEMA_VERSION = "2026.10-v2"


def _ensure_registry(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(64) PRIMARY KEY, applied_at VARCHAR(40))"))


def _applied(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        return {r[0] for r in conn.execute(text("SELECT version FROM schema_migrations"))}


def _mark(engine: Engine, version: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO schema_migrations (version, applied_at) VALUES (:v, :t)"),
                     {"v": version, "t": datetime.now(timezone.utc).isoformat()})


def add_missing_columns(engine: Engine) -> list[str]:
    """Adds every model column that is missing from an existing table. Returns 'table.column' names added."""
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    added: list[str] = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # create_all created it with every column
        have = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in have:
                continue
            ctype = col.type.compile(dialect=engine.dialect)
            ddl = f'ALTER TABLE {table.name} ADD COLUMN {col.name} {ctype}'
            if col.server_default is not None and hasattr(col.server_default, "arg"):
                arg = col.server_default.arg
                val = arg.text if hasattr(arg, "text") else str(arg)
                ddl += f" DEFAULT '{val}'" if not val.replace(".", "").isdigit() else f" DEFAULT {val}"
            with engine.begin() as conn:
                conn.execute(text(ddl))
            added.append(f"{table.name}.{col.name}")
    if added:
        log.info("schema migration: added columns %s", ", ".join(added))
    return added


def _backfill_citation_pages(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE citations SET page = (SELECT page FROM document_chunks WHERE document_chunks.id = citations.chunk_id) "
            "WHERE page IS NULL AND chunk_id IS NOT NULL"))


BACKFILLS = [
    ("2026.10-citation-pages", _backfill_citation_pages),
]


def migrate(engine: Engine) -> dict:
    """Run after `Base.metadata.create_all(engine)`."""
    _ensure_registry(engine)
    added = add_missing_columns(engine)
    done = _applied(engine)
    ran = []
    for version, fn in BACKFILLS:
        if version in done:
            continue
        try:
            fn(engine)
            _mark(engine, version)
            ran.append(version)
        except Exception as exc:  # a failed backfill must never stop the API from starting
            log.warning("backfill %s failed (will retry next start): %s", version, exc)
    if SCHEMA_VERSION not in done:
        _mark(engine, SCHEMA_VERSION)
    return {"columns_added": added, "backfills": ran, "schema_version": SCHEMA_VERSION}
