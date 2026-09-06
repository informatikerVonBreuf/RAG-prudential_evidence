from __future__ import annotations

import re
import sqlite3
import time
import uuid

from app.domain.models import (
    AnalyticalTrace,
    AnswerPayload,
    AnswerStatus,
    Claim,
    CoverageItem,
    EvidenceView,
    NarrativeContext,
    QuestionRequest,
    RetrievalRunTrace,
)
from app.retrieval.lexical import BM25Index
from app.store.artifacts import ArtifactStore

ANALYTICAL_MARKERS = {
    "compare",
    "comparaison",
    "comparer",
    "classement",
    "classer",
    "moyenne",
    "moyen",
    "average",
    "highest",
    "lowest",
    "plus eleve",
    "plus élevé",
    "plus faible",
    "ranking",
}


class PrudentialAnalytics:
    """Execute allow-listed SQL templates over promoted, source-linked facts."""

    def __init__(self, store: ArtifactStore) -> None:
        self.store = store

    def can_handle(self, question: str) -> bool:
        normalized = question.casefold()
        if len(set(re.findall(r"\b20\d{2}\b", normalized))) > 1:
            return False
        has_operation = any(marker in normalized for marker in ANALYTICAL_MARKERS)
        has_metric = any(
            marker in normalized
            for marker in ("scr", "solvabil", "coverage", "couverture", "fonds propres")
        )
        return has_operation and has_metric

    def answer(self, request: QuestionRequest) -> AnswerPayload:
        started = time.perf_counter()
        selected_ids = self.store.validate_document_ids(request.scope.document_ids)
        if not selected_ids:
            selected_ids = [document.id for document in self.store.public_documents]
        metric_ids, metric_label = self._metric(request.question)
        operation = self._operation(request.question)
        rows, sql, parameters = self._execute(
            selected_ids,
            metric_ids,
            request.constraints.entity,
            request.constraints.period,
            operation,
        )
        narrative_context = self._narrative_context(request, selected_ids, rows)
        evidence: list[EvidenceView] = []
        claims: list[Claim] = []
        for index, row in enumerate(rows, 1):
            chunk = next(chunk for chunk in self.store.chunks if chunk.id == row["chunk_id"])
            fact = next(fact for fact in chunk.facts if fact.field_id == row["field_id"])
            evidence_id = f"analytics-{index}"
            evidence.append(
                EvidenceView(
                    id=evidence_id,
                    field_id=fact.field_id,
                    field_label=fact.label,
                    state="ACCEPTED",
                    excerpt=chunk.text,
                    fact=fact,
                    source=chunk.locator,
                    reason=(
                        "Valeur promue interrogée par une requête SQL paramétrée en lecture seule."
                    ),
                )
            )
            claims.append(
                Claim(
                    id=f"claim-{index}",
                    text=f"{fact.entity} : {fact.formatted_value} ({fact.period}).",
                    evidence_ids=[evidence_id],
                )
            )
        status = AnswerStatus.COMPLETE if rows else AnswerStatus.NOT_FOUND
        if operation == "average" and rows:
            average = sum(float(row["value"]) for row in rows) / len(rows)
            summary = f"Moyenne calculée sur {len(rows)} entités : {average:.1f} %."
        elif operation == "highest" and rows:
            summary = f"Valeur la plus élevée : {claims[0].text}"
        elif rows:
            summary = f"Comparaison exhaustive de {len(rows)} valeurs promues : " + " ".join(
                claim.text for claim in claims
            )
        else:
            summary = (
                "Aucune valeur promue compatible avec le périmètre, l’entité "
                "et la période demandés."
            )
        if narrative_context:
            summary += (
                f" {len(narrative_context)} passage(s) narratif(s) connexe(s) "
                "sont fournis séparément pour l’interprétation."
            )
        field_id = metric_ids[0]
        return AnswerPayload(
            request_id=str(uuid.uuid4()),
            mode=request.mode,
            status=status,
            profile_id="prudential_sql_comparison",
            profile_label=f"Analyse SQL — {metric_label}",
            summary=summary,
            claims=claims,
            evidence=evidence,
            coverage=[
                CoverageItem(
                    field_id=field_id,
                    label=metric_label,
                    state="COVERED" if rows else "MISSING",
                    evidence_ids=[item.id for item in evidence],
                )
            ],
            missing_fields=[] if rows else [metric_label],
            corpus_version=self.store.corpus_version,
            query_trace=[],
            latency_ms=round((time.perf_counter() - started) * 1000),
            generation_provider="deterministic-sql",
            model_calls=[],
            mapping_trace={
                "profile_id": "prudential_sql_comparison",
                "decision_source": "rules",
                "confidence": 1.0,
                "entity": request.constraints.entity,
                "period": request.constraints.period,
                "lexical_scores": {},
                "dense_scores": {},
                "ambiguities": [],
                "model_calls": [],
            },
            retrieval_run=RetrievalRunTrace(
                strategy="sql_analytics",
                dense_provider="not_used",
                rounds=1,
                k_history=[],
                stop_reason="contract_complete" if rows else "budget_exhausted",
            ),
            analytical_trace=AnalyticalTrace(
                route="sql_plus_rag" if narrative_context else "sql",
                intent=operation,
                sql=sql,
                parameters=parameters,
                row_count=len(rows),
                safety_controls=[
                    "allow-listed SELECT template",
                    "bound parameters",
                    "read-only in-memory database",
                    "promoted facts only",
                    "scope/entity/period filters",
                ],
            ),
            narrative_context=narrative_context,
        )

    def _narrative_context(
        self,
        request: QuestionRequest,
        selected_ids: list[str],
        rows: list[sqlite3.Row],
    ) -> list[NarrativeContext]:
        markers = ("explique", "explication", "contexte", "que dit", "why", "explain")
        if not rows or not any(marker in request.question.casefold() for marker in markers):
            return []
        leading_entity = str(rows[0]["entity"])
        chunks = [
            chunk
            for chunk in self.store.chunks
            if chunk.document_id in selected_ids
            and chunk.chunk_type not in {"verified_table_evidence", "table_row_group"}
        ]
        if not chunks:
            return []
        ranked = BM25Index(chunks).search(f"{leading_entity} solvabilité SCR contexte")[:2]
        return [
            NarrativeContext(excerpt=chunk.text[:500], source=chunk.locator)
            for chunk, score in ranked
            if score > 0
        ]

    def _execute(
        self,
        document_ids: list[str],
        metric_ids: list[str],
        entity: str | None,
        period: str | None,
        operation: str,
    ) -> tuple[list[sqlite3.Row], str, list[str]]:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute(
            "CREATE TABLE facts (chunk_id TEXT, document_id TEXT, field_id TEXT, "
            "entity TEXT, period TEXT, value REAL, unit TEXT)"
        )
        for chunk in self.store.chunks:
            for fact in chunk.facts:
                if isinstance(fact.value, (int, float)):
                    connection.execute(
                        "INSERT INTO facts VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            chunk.id,
                            chunk.document_id,
                            fact.field_id,
                            fact.entity,
                            fact.period,
                            float(fact.value),
                            fact.unit,
                        ),
                    )
        doc_slots = ",".join("?" for _ in document_ids)
        metric_slots = ",".join("?" for _ in metric_ids)
        sql = (
            "SELECT chunk_id, document_id, field_id, entity, period, value, unit "
            f"FROM facts WHERE document_id IN ({doc_slots}) "
            f"AND field_id IN ({metric_slots})"
        )
        parameters = [*document_ids, *metric_ids]
        if entity:
            sql += " AND lower(entity) = lower(?)"
            parameters.append(entity)
        if period:
            sql += " AND period LIKE ?"
            parameters.append(f"{period}%")
        sql += " ORDER BY value " + ("ASC" if operation == "lowest" else "DESC")
        if operation in {"highest", "lowest"}:
            sql += " LIMIT 1"
        rows = list(connection.execute(sql, parameters))
        connection.close()
        return rows, sql, [str(item) for item in parameters]

    @staticmethod
    def _metric(question: str) -> tuple[list[str], str]:
        normalized = question.casefold()
        if "fonds propres" in normalized:
            return ["eligible_own_funds_scr"], "Fonds propres éligibles"
        if (
            "ratio" in normalized
            or "couverture" in normalized
            or "coverage" in normalized
            or "solvabil" in normalized
        ):
            return ["scr_coverage_ratio"], "Ratio de couverture du SCR"
        return ["group_scr", "entity_scr"], "Capital de solvabilité requis"

    @staticmethod
    def _operation(question: str) -> str:
        normalized = re.sub(r"\s+", " ", question.casefold())
        if "moyen" in normalized or "average" in normalized:
            return "average"
        if "plus faible" in normalized or "lowest" in normalized:
            return "lowest"
        if "plus élevé" in normalized or "plus eleve" in normalized or "highest" in normalized:
            return "highest"
        return "compare"
