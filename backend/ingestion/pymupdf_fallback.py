from __future__ import annotations

import importlib.metadata
import re
from pathlib import Path

from ingestion.models import PageArtifact, Provenance, TableArtifact, TableCellArtifact

QRT_TEMPLATES = {
    "S.23.01.22": {
        "R0660": (
            "Total eligible own funds to meet the consolidated group SCR",
            "currency",
            "thousand EUR",
        ),
        "R0680": ("Consolidated group SCR", "currency", "thousand EUR"),
        "R0690": ("Ratio of eligible own funds to consolidated group SCR", "ratio", "ratio"),
    },
    "S.23.01.01": {
        "R0540": ("Eligible own funds to meet the SCR", "currency", "thousand EUR"),
        "R0580": ("SCR", "currency", "thousand EUR"),
        "R0620": ("Ratio of eligible own funds to SCR", "ratio", "ratio"),
    },
}


def version() -> str:
    return importlib.metadata.version("pymupdf")


def extract_pages(path: Path, render_directory: Path | None = None) -> list[PageArtifact]:
    import pymupdf

    pages: list[PageArtifact] = []
    if render_directory:
        render_directory.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document):
            text = page.get_text("text", sort=True)
            image_path = None
            if render_directory:
                target = render_directory / f"page_{page_index + 1:03d}.png"
                page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False).save(target)
                image_path = target.as_posix()
            pages.append(
                PageArtifact(
                    page=page_index + 1,
                    text=text,
                    characters=len(text),
                    blocks=len(page.get_text("blocks")),
                    potential_scan=len(text.strip()) < 40,
                    image_path=image_path,
                )
            )
    return pages


def extract_qrt_coverage_table(
    path: Path, entity: str, period: str
) -> tuple[TableArtifact | None, list[str]]:
    import pymupdf

    warnings: list[str] = []
    cells: list[TableCellArtifact] = []
    selected_template: str | None = None
    expected_cells: dict[str, tuple[str, str, str]] = {}
    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document):
            text = page.get_text("text", sort=True)
            template_id = next(
                (template for template in QRT_TEMPLATES if template in text), None
            )
            if template_id is None:
                continue
            selected_template = template_id
            expected_cells = QRT_TEMPLATES[template_id]
            for row_code, (label, value_type, unit) in expected_cells.items():
                matches = page.search_for(row_code)
                if not matches:
                    continue
                row_box = matches[0]
                words_to_right = [
                    word
                    for word in page.get_text("words")
                    if abs(word[1] - row_box.y0) < 1.5 and word[0] > row_box.x1
                ]
                numeric = _first_numeric_word(words_to_right)
                if numeric is None:
                    warnings.append(f"Value not found for {row_code} on page {page_index + 1}")
                    continue
                raw_value, normalized, value_box = numeric
                bbox = list(row_box | value_box)
                cells.append(
                    TableCellArtifact(
                        row_code=row_code,
                        column_code="C0010",
                        row_label=label,
                        raw_value=raw_value,
                        normalized_value=normalized,
                        value_type=value_type,
                        unit=unit,
                        provenance=Provenance(
                            page=page_index + 1,
                            bbox=[round(value, 2) for value in bbox],
                            source_kind="native_pdf_text_verified",
                        ),
                    )
                )
    if not selected_template or {cell.row_code for cell in cells} != set(expected_cells):
        expected = "/".join(expected_cells) if expected_cells else "SCR coverage"
        warnings.append(f"The expected QRT evidence cells ({expected}) were not fully extracted.")
        return None, warnings
    return (
        TableArtifact(
            id=selected_template,
            title="Own funds and solvency capital requirement",
            entity=entity,
            period=period,
            pages=sorted({cell.provenance.page for cell in cells}),
            cells=cells,
        ),
        warnings,
    )


def _first_numeric_word(words: list[tuple[object, ...]]) -> tuple[str, float, object] | None:
    import pymupdf

    for word in words:
        raw = str(word[4])
        if not re.fullmatch(r"(?:\d{1,3}(?:\.\d{3})+|\d+[,\.]\d+|\d+)", raw):
            continue
        if "," in raw:
            normalized = float(raw.replace(".", "").replace(",", "."))
        elif raw.count(".") > 1 or (
            raw.count(".") == 1 and len(raw.rsplit(".", 1)[1]) == 3
        ):
            normalized = float(raw.replace(".", ""))
        else:
            normalized = float(raw)
        return raw, normalized, pymupdf.Rect(word[:4])
    return None
