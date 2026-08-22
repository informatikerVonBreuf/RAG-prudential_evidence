from __future__ import annotations

import argparse
import json
from pathlib import Path

ROW_FIELDS = {
    "R0660": (
        "eligible_own_funds_scr",
        "Eligible own funds covering total group SCR",
        "currency",
    ),
    "R0680": ("group_scr", "Total group Solvency Capital Requirement", "currency"),
    "R0690": ("scr_coverage_ratio", "Total group SCR coverage ratio", "percentage"),
    "R0540": ("eligible_own_funds_scr", "Eligible own funds covering the SCR", "currency"),
    "R0580": ("entity_scr", "Solvency Capital Requirement", "currency"),
    "R0620": ("scr_coverage_ratio", "SCR coverage ratio", "percentage"),
}


def runtime_section_path(chunk: dict[str, object]) -> list[str]:
    """Guarantee a reviewable locator even for cover-page or unsectioned visuals."""
    section_path = chunk.get("section_path")
    if isinstance(section_path, list) and section_path:
        return [str(item) for item in section_path]
    return [f"Page {chunk['page_start']}", "Unsectioned content"]


def compile_runtime_corpus(base_path: Path, processed_directory: Path, output_path: Path) -> None:
    corpus = json.loads(base_path.read_text(encoding="utf-8"))
    manifest = json.loads((processed_directory / "manifest.json").read_text(encoding="utf-8"))
    facts = [
        json.loads(line)
        for line in (processed_directory / "facts.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    extracted_chunks = [
        json.loads(line)
        for line in (processed_directory / "chunks.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    document_id = manifest["document_id"]
    corpus["documents"] = [item for item in corpus["documents"] if item["id"] != document_id]
    corpus["chunks"] = [item for item in corpus["chunks"] if item["document_id"] != document_id]
    corpus["documents"].append(
        {
            "id": document_id,
            "folder": _folder(manifest["profile"]),
            "title": manifest["title"],
            "entity": manifest["entity"],
            "year": int(manifest["period"][:4]),
            "document_type": _document_type(manifest["profile"]),
            "version": f"{manifest['period']} / sha256-{manifest['sha256'][:16]}",
            "source_url": manifest["source_url"],
            "status": "reviewed",
            "pages": _count_lines(processed_directory / "pages.jsonl"),
            "description": _description(manifest["profile"]),
        }
    )
    version = f"{manifest['period']} / sha256-{manifest['sha256'][:16]}"
    for chunk in extracted_chunks:
        if chunk["chunk_type"] == "table_row_group":
            continue
        provenance = chunk.get("provenance", [])
        first_provenance = provenance[0] if provenance else {}
        corpus["chunks"].append(
            {
                "id": chunk["id"],
                "document_id": document_id,
                "chunk_type": chunk["chunk_type"],
                "text": chunk["contextualized_text"],
                "locator": {
                    "document_id": document_id,
                    "document_title": manifest["title"],
                    "version": version,
                    "source_url": manifest["source_url"],
                    "page": chunk["page_start"],
                    "section_path": runtime_section_path(chunk),
                    "bbox": first_provenance.get("bbox"),
                },
                "facts": [],
            }
        )
    for fact in facts:
        if fact["row_code"] not in ROW_FIELDS:
            continue
        field_id, label, value_type = ROW_FIELDS[fact["row_code"]]
        value = fact["normalized_value"]
        unit = fact["unit"]
        formatted = _format_value(fact["row_code"], value, unit)
        corpus["chunks"].append(
            {
                "id": (
                    f"{document_id}-{fact['table_id'].casefold().replace('.', '')}-"
                    f"{fact['row_code'].casefold()}-{fact['column_code'].casefold()}"
                ),
                "document_id": document_id,
                "chunk_type": "verified_table_evidence",
                "text": (
                    f"{fact['table_id']} — {fact['row_code']}/{fact['column_code']}: "
                    f"{fact['row_label']}: "
                    f"{fact['raw_value']}."
                ),
                "locator": {
                    "document_id": document_id,
                    "document_title": manifest["title"],
                    "version": version,
                    "source_url": manifest["source_url"],
                    "page": fact["provenance"]["page"],
                    "section_path": [fact["table_id"], "Fonds propres"],
                    "table_id": fact["table_id"],
                    "row": fact["row_code"],
                    "column": fact["column_code"],
                    "bbox": fact["provenance"]["bbox"],
                },
                "facts": [
                    {
                        "field_id": field_id,
                        "label": label,
                        "value": value * 100 if value_type == "percentage" else value,
                        "formatted_value": formatted,
                        "value_type": value_type,
                        "unit": "%" if value_type == "percentage" else unit,
                        "period": f"{manifest['period']}-12-31",
                        "entity": manifest["entity"],
                    }
                ],
            }
        )
    output_path.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _count_lines(path: Path) -> int:
    return sum(bool(line.strip()) for line in path.read_text(encoding="utf-8").splitlines())


def _format_value(row_code: str, value: float, unit: str) -> str:
    if row_code in {"R0620", "R0690"}:
        return f"{value * 100:.0f} %"
    if unit in {"milliers EUR", "thousand EUR"}:
        return f"{value:,.0f} kEUR".replace(",", " ")
    return str(value)


def _folder(profile: str) -> str:
    return "Foyer / SFCR Annexes" if profile == "qrt_table_heavy" else "Foyer / Reports"


def _document_type(profile: str) -> str:
    return "Official public QRT PDF" if profile == "qrt_table_heavy" else "Official narrative PDF"


def _description(profile: str) -> str:
    if profile == "qrt_table_heavy":
        return "Offline-extracted artifact with explicitly verified prudential cells."
    return "Offline-extracted narrative artifact with page-level provenance."


def main() -> None:
    parser = argparse.ArgumentParser(description="Compiler les artefacts revus pour le runtime")
    parser.add_argument("--base", type=Path, default=Path("backend/app/data/corpus.json"))
    parser.add_argument("--processed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compile_runtime_corpus(args.base, args.processed, args.output)


if __name__ == "__main__":
    main()
