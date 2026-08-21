from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from ingestion.models import IngestionResult


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: Iterable[BaseModel]) -> None:
    path.write_text(
        "".join(
            json.dumps(value.model_dump(mode="json"), ensure_ascii=False) + "\n"
            for value in values
        ),
        encoding="utf-8",
    )


def write_result(result: IngestionResult) -> Path:
    output = result.output_path()
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "manifest.json", result.manifest.model_dump(mode="json"))
    _write_jsonl(output / "pages.jsonl", result.pages)
    _write_json(
        output / "sections.json",
        [item.model_dump(mode="json") for item in result.sections],
    )
    _write_jsonl(output / "tables.jsonl", result.tables)
    _write_jsonl(output / "figures.jsonl", result.figures)
    _write_jsonl(output / "chunks.jsonl", result.chunks)
    facts = [
        {"table_id": table.id, **cell.model_dump(mode="json")}
        for table in result.tables
        for cell in table.cells
    ]
    _write_jsonl_models_or_dicts(output / "facts.jsonl", facts)
    _write_json(output / "references.json", [])
    return output


def _write_jsonl_models_or_dicts(path: Path, values: Iterable[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values),
        encoding="utf-8",
    )
