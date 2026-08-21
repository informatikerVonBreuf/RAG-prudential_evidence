from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

from ingestion.models import FigureArtifact


class VisualObservation(BaseModel):
    label: str
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    source: str
    directly_visible: bool


class VisualDescription(BaseModel):
    image_type: str
    title: str | None = None
    entity: str | None = None
    observations: list[VisualObservation] = Field(default_factory=list)
    factual_description: str
    uncertainties: list[str] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)


def should_enrich_visual(figure: FigureArtifact) -> bool:
    if figure.classification in {"logo", "decorative", "photo", "signature"}:
        return False
    return figure.classification in {"chart", "diagram", "embedded_table"} or bool(
        figure.caption or figure.preceding_text or figure.following_text
    )


def describe_with_gemini(figure: FigureArtifact) -> VisualDescription:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_GENERATION_MODEL", "").strip()
    if not api_key or not model:
        raise RuntimeError("Configurer GEMINI_API_KEY et GEMINI_GENERATION_MODEL.")
    if not figure.image_path or not Path(figure.image_path).is_file():
        raise ValueError("La figure doit référencer une image locale existante.")
    from google import genai

    prompt = (
        "Analyse ce visuel financier public sans inventer. Sépare les informations "
        "directement visibles de celles fournies par le contexte. Retourne le schéma JSON "
        "demandé. Valeur illisible = null.\n"
        f"Section: {' > '.join(figure.section_path)}\nLégende: {figure.caption}\n"
        f"Avant: {' '.join(figure.preceding_text)}\nAprès: {' '.join(figure.following_text)}"
    )
    client = genai.Client(api_key=api_key)
    image_bytes = Path(figure.image_path).read_bytes()
    response = client.models.generate_content(
        model=model,
        contents=[prompt, genai.types.Part.from_bytes(data=image_bytes, mime_type="image/png")],
        config={"response_mime_type": "application/json", "response_schema": VisualDescription},
    )
    return VisualDescription.model_validate_json(response.text)
