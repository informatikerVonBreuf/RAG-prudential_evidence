from __future__ import annotations

from app.domain.models import AnswerStatus, Claim, EvidenceView, Mode

STATUS_INTROS = {
    AnswerStatus.COMPLETE: "Le contrat de preuves est entièrement couvert.",
    AnswerStatus.PARTIAL: "La réponse est limitée aux éléments effectivement couverts.",
    AnswerStatus.NOT_FOUND: "Le corpus sélectionné ne contient aucune preuve admissible.",
    AnswerStatus.CONFLICT: "Des preuves incompatibles doivent être examinées avant conclusion.",
}


class GroundedComposer:
    """Composes only from evidence accepted by code; it never invents missing fields."""

    def compose(
        self,
        question: str,
        mode: Mode,
        status: AnswerStatus,
        evidence: list[EvidenceView],
        missing_fields: list[str],
    ) -> tuple[str, list[Claim]]:
        accepted = [item for item in evidence if item.state == "ACCEPTED" and item.fact]
        conflicts = [item for item in evidence if item.state == "CONFLICT" and item.fact]
        claim_source = accepted if status != AnswerStatus.CONFLICT else conflicts
        claims = [
            Claim(
                id=f"claim-{index}",
                text=self._claim_text(item),
                evidence_ids=[item.id],
            )
            for index, item in enumerate(claim_source, 1)
        ]

        if mode == Mode.QUICK and len(claims) > 2:
            claims = claims[:2]

        intro = STATUS_INTROS[status]
        if not claims:
            summary = intro
        elif mode == Mode.SUMMARY:
            summary = f"{intro} Synthèse structurée : " + " ".join(
                f"{index}. {claim.text}" for index, claim in enumerate(claims, 1)
            )
        else:
            summary = f"{intro} " + " ".join(claim.text for claim in claims)

        if missing_fields:
            summary += " Champs non établis : " + ", ".join(missing_fields) + "."
        if status == AnswerStatus.CONFLICT:
            summary += " Les valeurs sont conservées côte à côte ; aucune moyenne n'est calculée."
        return summary, claims

    @staticmethod
    def _claim_text(evidence: EvidenceView) -> str:
        assert evidence.fact is not None
        fact = evidence.fact
        period = f" pour {fact.period}" if fact.period else ""
        return f"{fact.label} : {fact.formatted_value}{period} ({fact.entity})."

