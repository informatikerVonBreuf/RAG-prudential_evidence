from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import Literal

from app.domain.models import EvidenceView, ModelCallTrace


@dataclass(frozen=True)
class GenerationResult:
    text: str | None
    provider: str
    trace: ModelCallTrace


class OptionalGeminiComposer:
    """Optional grounded reformulation. Completeness always remains owned by the gate."""

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv("GEMINI_GENERATION_MODEL", "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    def compose(self, question: str, evidence: list[EvidenceView]) -> GenerationResult:
        started = time.perf_counter()
        accepted = [item for item in evidence if item.state == "ACCEPTED" and item.fact]
        if not self.enabled:
            return self._outcome(
                started, "DISABLED", 0, "Clé ou modèle Gemini non configuré."
            )
        if not accepted:
            return self._outcome(
                started, "FALLBACK", 0, "Aucune preuve acceptée à transmettre."
            )
        try:
            from google import genai
        except ImportError:
            return self._outcome(started, "ERROR", 0, "SDK google-genai non installé.")

        facts = "\n".join(
            f"- [{item.id}] {item.fact.label}: {item.fact.formatted_value}; "
            f"entité={item.fact.entity}; période={item.fact.period}"
            for item in accepted
            if item.fact
        )
        prompt = (
            "Tu reformules une réponse documentaire en français. Utilise uniquement les "
            "preuves ci-dessous. Ne complète aucune information manquante. Conserve les "
            "identifiants de preuve entre crochets après chaque affirmation.\n\n"
            f"Question: {question}\nPreuves:\n{facts}"
        )
        client = genai.Client(api_key=self.api_key)
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=self.model, contents=prompt)
                text = (response.text or "").strip()
                if text and all(item.id in text for item in accepted):
                    return GenerationResult(
                        text=text,
                        provider=f"gemini:{self.model}",
                        trace=ModelCallTrace(
                            provider="gemini",
                            model=self.model,
                            purpose="grounded_answer_composition",
                            status="SUCCESS",
                            attempts=attempt + 1,
                            latency_ms=round((time.perf_counter() - started) * 1000),
                            detail="Réponse reçue et identifiants de preuve vérifiés.",
                        ),
                    )
                return self._outcome(
                    started,
                    "FALLBACK",
                    attempt + 1,
                    "Sortie sans tous les identifiants de preuve requis.",
                )
            except Exception:  # provider errors must never break deterministic fallback
                if attempt == 2:
                    return self._outcome(
                        started,
                        "ERROR",
                        attempt + 1,
                        "Échec fournisseur après reprises techniques bornées.",
                    )
                time.sleep((2**attempt) + random.random() * 0.2)
        return self._outcome(started, "ERROR", 3, "Échec fournisseur.")

    def _outcome(
        self,
        started: float,
        status: Literal["DISABLED", "SUCCESS", "FALLBACK", "ERROR"],
        attempts: int,
        detail: str,
    ) -> GenerationResult:
        return GenerationResult(
            text=None,
            provider="deterministic",
            trace=ModelCallTrace(
                provider="gemini",
                model=self.model or None,
                purpose="grounded_answer_composition",
                status=status,
                attempts=attempts,
                latency_ms=round((time.perf_counter() - started) * 1000),
                detail=detail,
            ),
        )
