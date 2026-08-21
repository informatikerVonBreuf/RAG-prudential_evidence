from __future__ import annotations

import importlib.metadata
import re
from pathlib import Path

from ingestion.models import PageArtifact, Provenance, TableArtifact, TableCellArtifact

QRT_CELLS = {
    "R0660": (
        "Total des fonds propres éligibles pour couvrir le SCR total du groupe",
        "currency",
        "milliers EUR",
    ),
    "R0680": ("Capital de solvabilité requis total du groupe", "currency", "milliers EUR"),
    "R0690": ("Ratio total des fonds propres éligibles sur SCR total du groupe", "ratio", "ratio"),
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
    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document):
            text = page.get_text("text", sort=True)
            if "S.23.01.22" not in text:
                continue
            for row_code, (label, value_type, unit) in QRT_CELLS.items():
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
                    warnings.append(f"Valeur introuvable pour {row_code} page {page_index + 1}")
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
    if {cell.row_code for cell in cells} != set(QRT_CELLS):
        warnings.append("Le triplet QRT R0660/R0680/R0690 n'est pas entièrement extrait.")
        return None, warnings
    return (
        TableArtifact(
            id="S.23.01.22",
            title="Fonds propres",
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
