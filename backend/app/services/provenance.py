"""Data provenance & verification.

Every knowledge object gets one `Provenance` row. Defaults are *derived* from what the record already says about
itself (is_demo flags, station `verified` facts, dataset synthetic source, uploader) so that nothing is ever
labelled more trustworthy than it is. Demonstration and synthetic records can never be promoted to VERIFIED or
PARTNER SOURCE — that guard lives in `validate_status_change`.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Dataset,
    Document,
    Expedition,
    GeneratedContent,
    InstitutionalActivity,
    Media,
    Provenance,
    Researcher,
    Station,
)

VERIFICATION = {
    "verified": ("Verified", "Facts checked against a named, public source."),
    "partner_source": ("Partner source", "Supplied by a partner institution under an agreement."),
    "user_uploaded": ("User uploaded", "Added by a signed-in user; not yet verified by an administrator."),
    "pending_review": ("Pending review", "Awaiting verification or editorial review."),
    "demo_data": ("Demo data", "Prototype demonstration record — illustrative, not an institutional record."),
    "synthetic_demo": ("Synthetic demonstration", "Synthetic values generated for prototype evaluation — not observations."),
    "unverified": ("Unverified", "Provenance has not been established."),
}
DEMO_STATUSES = {"demo_data", "synthetic_demo"}
TRUSTED_STATUSES = {"verified", "partner_source"}
OFFICIAL_SOURCE_TYPE = "Official public information"

# UI filter label -> predicate on a provenance dict
FILTERS = {
    "Verified": lambda p: p["verification_status"] == "verified",
    "Official": lambda p: p["source_type"] == OFFICIAL_SOURCE_TYPE and p["verification_status"] == "verified",
    "Partner": lambda p: p["verification_status"] == "partner_source",
    "Uploaded": lambda p: p["verification_status"] == "user_uploaded",
    "Demo": lambda p: p["verification_status"] == "demo_data",
    "Synthetic": lambda p: p["verification_status"] == "synthetic_demo",
    "Pending": lambda p: p["verification_status"] in {"pending_review", "unverified"},
}

MODELS = {"document": Document, "dataset": Dataset, "media": Media, "expedition": Expedition, "station": Station,
          "researcher": Researcher, "activity": InstitutionalActivity}

DEMO_NOTICE = ("This record contains prototype demonstration content used for evaluation. It is not an official "
               "NCPOR / MoES record.")
SYNTH_NOTICE = ("This record contains synthetic demonstration values used for prototype evaluation. "
                "They are not observations.")


def _d(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    return v if isinstance(v, date) else None


def default_provenance(rtype: str, obj) -> dict:
    """Best honest description of a record's origin, derived from the record itself."""
    created = getattr(obj, "created_at", None)
    base = dict(source_organisation="", source_type="", source_url="", original_identifier=getattr(obj, "slug", ""),
                license="", publication_date=None, collection_date=None, imported_at=created, last_verified_at=None,
                verification_status="unverified", verified_by="", data_quality="", provenance_notes="")
    if rtype == "document":
        if obj.is_demo:
            base.update(source_organisation=obj.institution, source_type="Prototype demonstration document",
                        license="Demonstration content — not for citation", publication_date=date(obj.year, 1, 1) if obj.year else None,
                        verification_status="demo_data", data_quality="Illustrative",
                        provenance_notes="Text written for the PolarNexus prototype. Not an official NCPOR/MoES publication.")
        else:
            base.update(source_organisation=obj.institution or "", source_type="Researcher upload",
                        original_identifier=obj.file_name or obj.slug, verification_status="user_uploaded",
                        data_quality="Not yet assessed", provenance_notes=f"{obj.source}. Awaiting administrator verification.")
    elif rtype == "dataset":
        synthetic = obj.is_demo or "synthetic" in (obj.source or "").lower() or "synthetic" in (obj.license or "").lower()
        base.update(source_organisation=obj.source, source_type="Synthetic demonstration dataset" if synthetic else "Dataset",
                    license=obj.license, collection_date=_d(obj.temporal_start),
                    verification_status="synthetic_demo" if synthetic else "user_uploaded",
                    data_quality="Synthetic — not observations" if synthetic else "Not yet assessed",
                    provenance_notes=SYNTH_NOTICE if synthetic else "")
    elif rtype == "media":
        if obj.is_demo:
            base.update(source_organisation="PolarNexus prototype", source_type="Original generated artwork",
                        license=obj.license, verification_status="demo_data", data_quality="Illustrative",
                        provenance_notes="Placeholder artwork standing in for institutional media.")
        else:
            base.update(source_organisation=obj.credit, source_type="User upload", license=obj.license,
                        original_identifier=obj.filename or obj.slug, collection_date=_d(obj.captured_at),
                        verification_status="user_uploaded", data_quality="Not yet assessed",
                        provenance_notes="Uploaded through the media ingestion pipeline. Awaiting verification.")
    elif rtype == "expedition":
        if obj.is_demo:
            base.update(source_organisation="PolarNexus prototype", source_type="Demonstration expedition record",
                        verification_status="demo_data", data_quality="Illustrative",
                        provenance_notes=obj.verified_note or "Illustrative expedition record created for the prototype.")
        else:
            base.update(source_organisation="NCPOR, Ministry of Earth Sciences — public expedition history",
                        source_type=OFFICIAL_SOURCE_TYPE, verification_status="verified",
                        verified_by="Prototype team (public sources)", data_quality="Partial — headline facts only",
                        provenance_notes=obj.verified_note)
    elif rtype == "station":
        if obj.verified:
            base.update(source_organisation=obj.facts_source, source_type=OFFICIAL_SOURCE_TYPE,
                        verification_status="verified", verified_by="Prototype team (public sources)",
                        data_quality="High-level facts only (location, coordinates, year established)",
                        provenance_notes="Only widely published, high-level facts are verified. Linked research is demonstration content.")
        else:
            base.update(source_organisation="PolarNexus prototype", source_type="Demonstration location",
                        verification_status="demo_data", data_quality="Illustrative",
                        provenance_notes="Illustrative field site used to connect demonstration records.")
    elif rtype == "researcher":
        base.update(source_organisation=obj.institution, source_type="Fictional demonstration profile",
                    verification_status="demo_data" if obj.is_demo else "user_uploaded", data_quality="Illustrative",
                    provenance_notes="Fictional person created for the prototype. Any resemblance is coincidental.")
    elif rtype == "activity":
        if obj.is_demo:
            base.update(source_organisation=obj.organisation, source_type="Demonstration activity record",
                        publication_date=obj.date, verification_status="demo_data", data_quality="Illustrative",
                        provenance_notes="Illustrative institutional activity created for the prototype.")
        else:
            base.update(source_organisation=obj.organisation, source_type="Institutional activity (admin entry)",
                        publication_date=obj.date, verification_status="pending_review", data_quality="Not yet assessed")
    return base


def content_provenance(c: GeneratedContent, reviewer_name: str | None = None) -> dict:
    """Outreach content provenance is derived from the review workflow (never stored, never editable)."""
    reviewed = c.status in {"approved", "published"}
    return dict(
        source_organisation="PolarNexus Content Studio", source_type="AI-assisted outreach derived from repository evidence",
        source_url="", original_identifier=f"content-{c.id}", license="", publication_date=_d(c.published_at),
        collection_date=None, imported_at=c.created_at, last_verified_at=c.approved_at,
        verification_status="verified" if reviewed else "pending_review",
        verified_by=(reviewer_name or "Editor") if reviewed else "",
        data_quality=f"Automated evidence check: {(c.evidence_check or {}).get('overall', 'not run')}",
        provenance_notes=("Approved by a human editor after an automated evidence check." if reviewed else
                          "Generated from cited repository passages; requires editorial approval before publication.")
        + (" Derived from demonstration documents." if c.is_demo else ""),
    )


def provenance_map(db: Session) -> dict[tuple[str, int], Provenance]:
    return {(p.resource_type, p.resource_id): p for p in db.scalars(select(Provenance))}


def as_dict(p: Provenance | dict) -> dict:
    if isinstance(p, dict):
        return dict(p)
    return {k: getattr(p, k) for k in ("source_organisation", "source_type", "source_url", "original_identifier",
                                        "license", "publication_date", "collection_date", "imported_at",
                                        "last_verified_at", "verification_status", "verified_by", "data_quality",
                                        "provenance_notes")}


def provenance_out(p: Provenance | dict) -> dict:
    d = as_dict(p)
    status = d["verification_status"] if d["verification_status"] in VERIFICATION else "unverified"
    label, description = VERIFICATION[status]
    for k in ("publication_date", "collection_date", "imported_at", "last_verified_at"):
        v = d.get(k)
        d[k] = v.isoformat() if v else None
    d.update(verification_status=status, verification_label=label, verification_description=description,
             is_demo=status in DEMO_STATUSES, official=d["source_type"] == OFFICIAL_SOURCE_TYPE and status == "verified",
             notice=SYNTH_NOTICE if status == "synthetic_demo" else DEMO_NOTICE if status == "demo_data" else "")
    return d


def get_provenance(db: Session, rtype: str, obj) -> dict:
    row = db.scalar(select(Provenance).where(Provenance.resource_type == rtype, Provenance.resource_id == obj.id))
    return provenance_out(row if row else default_provenance(rtype, obj))


def ensure_for(db: Session, rtype: str, obj, commit: bool = True) -> Provenance:
    row = db.scalar(select(Provenance).where(Provenance.resource_type == rtype, Provenance.resource_id == obj.id))
    if row:
        return row
    row = Provenance(resource_type=rtype, resource_id=obj.id, **default_provenance(rtype, obj))
    db.add(row)
    if commit:
        db.commit()
    return row


def ensure_all(db: Session) -> int:
    """Creates provenance rows for every resource that does not have one yet. Idempotent."""
    have = {(t, i) for t, i in db.execute(select(Provenance.resource_type, Provenance.resource_id))}
    n = 0
    for rtype, model in MODELS.items():
        for obj in db.scalars(select(model)):
            if (rtype, obj.id) not in have:
                db.add(Provenance(resource_type=rtype, resource_id=obj.id, **default_provenance(rtype, obj)))
                n += 1
    if n:
        db.commit()
    return n


def is_demo_record(rtype: str, obj) -> bool:
    if rtype == "station":
        return not obj.verified
    if rtype == "dataset":
        return default_provenance(rtype, obj)["verification_status"] == "synthetic_demo"
    return bool(getattr(obj, "is_demo", False))


def validate_status_change(rtype: str, obj, new_status: str) -> None:
    if new_status not in VERIFICATION:
        raise ValueError("Unknown verification status.")
    if new_status in TRUSTED_STATUSES and is_demo_record(rtype, obj):
        raise ValueError("Demonstration or synthetic records cannot be marked Verified or Partner source. "
                         "Replace them with a real, sourced record instead.")
