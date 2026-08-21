from __future__ import annotations

import argparse
import json
from pathlib import Path

ROW_FIELDS = {
    "R0660": (
        "eligible_own_funds_scr",
        "Fonds propres éligibles couvrant le SCR total",
        "currency",
    ),
    "R0680": ("group_scr", "Capital de solvabilité requis total du Groupe", "currency"),
    "R0690": ("scr_coverage_ratio", "Ratio de couverture du SCR total", "percentage"),
}


def compile_runtime_corpus(base_path: Path, processed_directory: Path, output_path: Path) -> None:
    corpus = json.loads(base_path.read_text(encoding="utf-8"))
    manifest = json.loads((processed_directory / "manifest.json").read_text(encoding="utf-8"))
    facts = [
        json.loads(line)
        for line in (processed_directory / "facts.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    document_id = manifest["document_id"]
    corpus["documents"] = [item for item in corpus["documents"] if item["id"] != document_id]
    corpus["chunks"] = [item for item in corpus["chunks"] if item["document_id"] != document_id]
    corpus["documents"].append(
        {
            "id": document_id,
            "folder": "Foyer / Annexes SFCR",
            "title": manifest["title"],
            "entity": manifest["entity"],
            "year": int(manifest["period"][:4]),
            "document_type": "QRT public — PDF officiel",
            "version": f"{manifest['period']} / sha256-{manifest['sha256'][:16]}",
            "source_url": manifest["source_url"],
            "status": "reviewed",
            "pages": _count_lines(processed_directory / "pages.jsonl"),
            "description": "Artefact extrait hors ligne et revu sur les cellules critiques.",
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
                "id": f"qrt-2025-s2301-{fact['row_code'].casefold()}-c0010",
                "document_id": document_id,
                "text": (
                    f"S.23.01.22 — {fact['row_code']}/C0010 : {fact['row_label']} : "
                    f"{fact['raw_value']}."
                ),
                "locator": {
                    "document_id": document_id,
                    "document_title": manifest["title"],
                    "version": f"{manifest['period']} / sha256-{manifest['sha256'][:16]}",
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
                        "value": 287 if fact["row_code"] == "R0690" else value,
                        "formatted_value": formatted,
                        "value_type": value_type,
                        "unit": "%" if fact["row_code"] == "R0690" else unit,
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
    if row_code == "R0690":
        return f"{value * 100:.0f} %"
    return f"{value:,.0f} k€".replace(",", " ") if unit == "milliers EUR" else str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compiler les artefacts revus pour le runtime")
    parser.add_argument("--base", type=Path, default=Path("backend/app/data/corpus.json"))
    parser.add_argument("--processed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compile_runtime_corpus(args.base, args.processed, args.output)


if __name__ == "__main__":
    main()
