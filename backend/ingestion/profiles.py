from __future__ import annotations

from pathlib import Path

from ingestion.models import DocumentProfile


def detect_document_profile(path: Path, sample_text: str = "") -> DocumentProfile:
    suffix = path.suffix.casefold()
    normalized = f"{path.name} {sample_text[:5000]}".casefold()
    if suffix in {".html", ".htm"}:
        return DocumentProfile.HTML_REPORT
    if "sfcr" in normalized or "solvency and financial condition report" in normalized:
        return DocumentProfile.NARRATIVE_POLICY
    if "qrt" in normalized or "s.23.01" in normalized:
        return DocumentProfile.QRT_TABLE_HEAVY
    if not sample_text.strip():
        return DocumentProfile.SCANNED_DOCUMENT
    if any(token in normalized for token in ("rapport annuel", "annual report")):
        return DocumentProfile.ANNUAL_REPORT_VISUAL
    return DocumentProfile.NARRATIVE_POLICY
