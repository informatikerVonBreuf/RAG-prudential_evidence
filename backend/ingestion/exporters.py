from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from ingestion.models import (
    ChunkArtifact,
    FigureArtifact,
    IngestionManifest,
    IngestionResult,
    PageArtifact,
    SectionArtifact,
    TableArtifact,
)


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


def read_result(output: Path) -> IngestionResult:
    """Reload cached artifacts without executing Docling again."""
    return IngestionResult(
        manifest=IngestionManifest.model_validate(_read_json(output / "manifest.json")),
        pages=_read_jsonl(output / "pages.jsonl", PageArtifact),
        sections=[
            SectionArtifact.model_validate(item)
            for item in _read_json(output / "sections.json")
        ],
        tables=_read_jsonl(output / "tables.jsonl", TableArtifact),
        figures=_read_jsonl(output / "figures.jsonl", FigureArtifact),
        chunks=_read_jsonl(output / "chunks.jsonl", ChunkArtifact),
    )


def write_canonical_markdown(result: IngestionResult, extracted_markdown: str) -> Path:
    """Write the reviewable textual source used before promotion to runtime."""
    manifest = result.manifest
    lines = [
        "---",
        f'document_id: "{manifest.document_id}"',
        f'title: "{manifest.title}"',
        f'entity: "{manifest.entity}"',
        f'period: "{manifest.period}"',
        f'source_url: "{manifest.source_url}"',
        f'sha256: "{manifest.sha256}"',
        f'extractor: "{manifest.extractor}"',
        f'extractor_version: "{manifest.extractor_version or "unknown"}"',
        "---",
        "",
        "# Extracted document content",
        "",
        extracted_markdown.strip(),
        "",
        "# Verified table evidence",
        "",
    ]
    if result.tables:
        for table in result.tables:
            lines.extend([f"## {table.id} — {table.title}", ""])
            lines.append(
                "| Row | Column | Label | Raw value | Normalized value | Unit | Page |"
            )
            lines.append("|---|---|---|---:|---:|---|---:|")
            for cell in table.cells:
                lines.append(
                    f"| {cell.row_code} | {cell.column_code} | {cell.row_label} | "
                    f"{cell.raw_value} | {cell.normalized_value} | {cell.unit} | "
                    f"{cell.provenance.page} |"
                )
            lines.append("")
    else:
        lines.extend(["No table cell has been verified.", ""])

    lines.extend(["# Visual descriptions", ""])
    if not result.figures:
        lines.append("No independent visual was extracted.")
    for figure in result.figures:
        image_name = Path(figure.image_path).name if figure.image_path else "non-disponible"
        review_image_path = f"assets/{manifest.document_id}/{image_name}"
        lines.extend([
            f"## Figure {figure.id} — page {figure.page}",
            "",
            f"- Classification: `{figure.classification}`",
            f"- Reviewed image: [{image_name}]({review_image_path})",
            f"- Preceding context: {' '.join(figure.preceding_text) or 'unavailable'}",
            f"- Following context: {' '.join(figure.following_text) or 'unavailable'}",
        ])
        if figure.description:
            lines.extend([
                "- Gemini enrichment: `SUCCESS`",
                "",
                f"```json\n{json.dumps(figure.description, ensure_ascii=False, indent=2)}\n```",
                "",
            ])
        else:
            lines.extend(["- Gemini enrichment: `NOT_RUN`", ""])

    path = result.output_path() / "document.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def _write_jsonl_models_or_dicts(path: Path, values: Iterable[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values),
        encoding="utf-8",
    )


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path, model: type[BaseModel]) -> list:
    return [
        model.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
