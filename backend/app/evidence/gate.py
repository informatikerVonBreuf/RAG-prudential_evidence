from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.domain.models import (
    AnswerStatus,
    Candidate,
    CoverageItem,
    EvidenceProfile,
    EvidenceView,
)


@dataclass(frozen=True)
class GateResult:
    status: AnswerStatus
    evidence: list[EvidenceView]
    coverage: list[CoverageItem]
    missing_fields: list[str]


class DeterministicEvidenceGate:
    def evaluate(
        self,
        profile: EvidenceProfile,
        candidates: list[Candidate],
    ) -> GateResult:
        candidates_by_field: dict[str, list[Candidate]] = defaultdict(list)
        for candidate in candidates:
            candidates_by_field[candidate.field_id].append(candidate)

        evidence: list[EvidenceView] = []
        coverage: list[CoverageItem] = []
        missing_fields: list[str] = []
        conflict_found = False

        for field in profile.fields:
            accepted: list[tuple[Candidate, object]] = []
            for candidate in candidates_by_field[field.id]:
                matching_facts = [
                    fact for fact in candidate.chunk.facts if fact.field_id == field.id
                ]
                for fact in matching_facts:
                    if fact.value_type == field.value_type:
                        accepted.append((candidate, fact))

            if not accepted:
                evidence_id = f"evidence-{field.id}-missing"
                evidence.append(
                    EvidenceView(
                        id=evidence_id,
                        field_id=field.id,
                        field_label=field.label,
                        state="MISSING",
                        reason="Aucune preuve typée et citée n'a été trouvée dans le périmètre.",
                    )
                )
                coverage.append(
                    CoverageItem(field_id=field.id, label=field.label, state="MISSING")
                )
                missing_fields.append(field.label)
                continue

            values_by_context: dict[tuple[str, str, str | None], set[str]] = defaultdict(set)
            for _, fact in accepted:
                context = (fact.entity, fact.field_id, fact.period)
                values_by_context[context].add(str(fact.value))
            is_conflict = any(len(values) > 1 for values in values_by_context.values())
            state = "CONFLICT" if is_conflict else "ACCEPTED"
            coverage_state = "CONFLICT" if is_conflict else "COVERED"
            conflict_found = conflict_found or is_conflict

            accepted_evidence_ids: list[str] = []
            for index, (candidate, fact) in enumerate(accepted[:2], 1):
                evidence_id = f"evidence-{field.id}-{index}"
                accepted_evidence_ids.append(evidence_id)
                evidence.append(
                    EvidenceView(
                        id=evidence_id,
                        field_id=field.id,
                        field_label=field.label,
                        state=state,
                        excerpt=candidate.chunk.text,
                        fact=fact,
                        source=candidate.chunk.locator,
                        score=candidate.score,
                        reason=(
                            "Plusieurs valeurs incompatibles existent pour la même "
                            "entité et période."
                            if is_conflict
                            else "Type, entité, période et provenance contrôlés par le gate."
                        ),
                    )
                )
            coverage.append(
                CoverageItem(
                    field_id=field.id,
                    label=field.label,
                    state=coverage_state,
                    evidence_ids=accepted_evidence_ids,
                )
            )

        if conflict_found:
            status = AnswerStatus.CONFLICT
        elif len(missing_fields) == len(profile.fields):
            status = AnswerStatus.NOT_FOUND
        elif missing_fields:
            status = AnswerStatus.PARTIAL
        else:
            status = AnswerStatus.COMPLETE
        return GateResult(status, evidence, coverage, missing_fields)
