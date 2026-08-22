from __future__ import annotations

from pathlib import Path
from typing import Any

from ingestion.models import FigureArtifact


def extract_figures(document: Any, output_directory: Path) -> list[FigureArtifact]:
    """Persist Docling pictures with enough context for optional visual enrichment."""
    from docling_core.types.doc import PictureItem, SectionHeaderItem, TextItem, TitleItem

    items = list(document.iterate_items(with_groups=False, traverse_pictures=True))
    figures: list[FigureArtifact] = []
    image_directory = output_directory / "figures"
    image_directory.mkdir(parents=True, exist_ok=True)
    headings: list[str] = []

    for index, (item, _level) in enumerate(items):
        if isinstance(item, TitleItem | SectionHeaderItem):
            headings = [item.text]
            continue
        if not isinstance(item, PictureItem) or not item.prov:
            continue
        image = item.get_image(document)
        if image is None:
            continue
        provenance = item.prov[0]
        image_path = image_directory / f"figure-{len(figures) + 1:03d}.png"
        image.save(image_path, format="PNG")
        preceding = _nearby_text(items, index, direction=-1, text_type=TextItem)
        following = _nearby_text(items, index, direction=1, text_type=TextItem)
        label = getattr(item.label, "value", str(item.label))
        figures.append(
            FigureArtifact(
                id=f"figure-{len(figures) + 1:03d}",
                page=provenance.page_no,
                section_path=headings,
                caption=item.caption_text(document) or None,
                preceding_text=preceding,
                following_text=following,
                classification="chart" if label == "chart" else "unknown",
                image_path=image_path.as_posix(),
                bbox=[round(value, 2) for value in provenance.bbox.as_tuple()],
            )
        )
    return figures


def _nearby_text(
    items: list[tuple[Any, int]], index: int, direction: int, text_type: type[Any]
) -> list[str]:
    texts: list[str] = []
    cursor = index + direction
    while 0 <= cursor < len(items) and len(texts) < 2:
        candidate = items[cursor][0]
        if isinstance(candidate, text_type) and candidate.text.strip():
            texts.append(candidate.text.strip())
        cursor += direction
    if direction < 0:
        texts.reverse()
    return texts
