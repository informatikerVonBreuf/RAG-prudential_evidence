from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models import EvidenceConstraints, EvidenceProfile, ModelCallTrace
from app.domain.profiles import OPEN_QUESTION_PROFILE, PROFILES, _trigger_score

ENTITY_ALIASES: dict[str, tuple[str, ...]] = {
    "Groupe Foyer": ("groupe foyer", "foyer group", "group foyer"),
    "Foyer Assurances S.A.": ("foyer assurances", "foyer assurance"),
    "Foyer Global Health S.A.": ("foyer global health", "global health", "fgh"),
}

PROFILE_EXAMPLES: dict[str, tuple[str, ...]] = {
    "prudential_coverage": (
        "What is Groupe Foyer's SCR coverage ratio?",
        "Group eligible own funds and solvency capital requirement",
        "Quelle est la couverture prudentielle du Groupe Foyer ?",
        "Fonds propres éligibles, SCR et ratio de solvabilité du Groupe",
    ),
    "entity_prudential_coverage": (
        "What is Foyer Assurances SCR coverage?",
        "Solvency ratio for Foyer Global Health legal entity",
        "Quel est le ratio de couverture SCR de Foyer Assurances ?",
        "Couverture du capital de solvabilité requis de Foyer Global Health",
    ),
    "public_position": (
        "What is the Group's public financial and market position?",
        "Equity, market share and business areas of Groupe Foyer",
        "Capitaux propres, part de marché et activités du Groupe Foyer",
    ),
    "customer_operations": (
        "Customer satisfaction, claims handling and insured households",
        "MyFoyer users and operational customer indicators",
        "Satisfaction clients, sinistres et ménages assurés",
    ),
    "international_health": (
        "Global Health countries, premiums and employees",
        "International health insurance activity key figures",
        "Pays, primes et effectifs de l'activité santé internationale",
    ),
}


class MappingDecision(BaseModel):
    profile_id: str
    entity: str | None = None
    period: str | None = None
    confidence: float = Field(ge=0, le=1)
    decision_source: Literal["explicit", "rules", "hybrid_dense", "llm_judge", "abstention"]
    lexical_scores: dict[str, float] = Field(default_factory=dict)
    dense_scores: dict[str, float] = Field(default_factory=dict)
    ambiguities: list[str] = Field(default_factory=list)
    model_calls: list[ModelCallTrace] = Field(default_factory=list)


@dataclass(frozen=True)
class MappedQuestion:
    profile: EvidenceProfile
    constraints: EvidenceConstraints
    decision: MappingDecision


def _normalize(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold()).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", folded))


def extract_entity(question: str) -> tuple[str | None, list[str]]:
    normalized = f" {_normalize(question)} "
    matches = [
        entity
        for entity, aliases in ENTITY_ALIASES.items()
        if any(f" {_normalize(alias)} " in normalized for alias in aliases)
    ]
    if len(matches) == 1:
        return matches[0], []
    if len(matches) > 1:
        return None, [f"multiple entities detected: {', '.join(matches)}"]
    return None, []


def canonicalize_entity(value: str) -> str:
    normalized = _normalize(value)
    for entity, aliases in ENTITY_ALIASES.items():
        accepted = {_normalize(entity), *(_normalize(alias) for alias in aliases)}
        if normalized in accepted:
            return entity
    return normalized


def extract_period(question: str) -> tuple[str | None, list[str]]:
    years = sorted(set(re.findall(r"\b(?:19|20)\d{2}\b", question)))
    if len(years) == 1:
        return years[0], []
    if len(years) > 1:
        return None, [f"multiple periods detected: {', '.join(years)}"]
    return None, []


class HybridQuestionMapper:
    """Rules first, Gemini dense fallback, bounded Gemini judge for ambiguity only."""

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "").strip()
        self.generation_model = os.getenv("GEMINI_GENERATION_MODEL", "").strip()
        self.online_enabled = os.getenv("ENABLE_HYBRID_MAPPING", "0") == "1"
        self._prototype_vectors: dict[str, list[float]] | None = None
        self._decision_cache: dict[str, MappedQuestion] = {}

    def map(
        self,
        question: str,
        explicit_profile_id: str | None = None,
        explicit_constraints: EvidenceConstraints | None = None,
    ) -> MappedQuestion:
        explicit_constraints = explicit_constraints or EvidenceConstraints()
        cache_key = json.dumps(
            {
                "question": _normalize(question),
                "profile": explicit_profile_id,
                "constraints": explicit_constraints.model_dump(mode="json"),
                "online": self.online_enabled,
            },
            sort_keys=True,
        )
        if cache_key not in self._decision_cache:
            self._decision_cache[cache_key] = self._map_uncached(
                question, explicit_profile_id, explicit_constraints
            )
        return self._decision_cache[cache_key]

    def _map_uncached(
        self,
        question: str,
        explicit_profile_id: str | None,
        explicit_constraints: EvidenceConstraints,
    ) -> MappedQuestion:
        entity, entity_ambiguities = extract_entity(question)
        period, period_ambiguities = extract_period(question)
        constraints = EvidenceConstraints(
            entity=explicit_constraints.entity or entity,
            period=explicit_constraints.period or period,
        )
        ambiguities = [*entity_ambiguities, *period_ambiguities]

        if explicit_profile_id:
            profile = self._profile(explicit_profile_id)
            return self._result(profile, constraints, 1.0, "explicit", {}, {}, ambiguities, [])

        unresolved_context = bool(
            (entity_ambiguities and not explicit_constraints.entity)
            or (period_ambiguities and not explicit_constraints.period)
        )
        if unresolved_context:
            return self._result(
                OPEN_QUESTION_PROFILE,
                constraints,
                0.0,
                "abstention",
                {},
                {},
                ambiguities,
                [],
            )

        lexical_scores = self._lexical_scores(question)
        ordered = sorted(lexical_scores.items(), key=lambda item: (-item[1], item[0]))
        best_id, best = ordered[0]
        runner_up = ordered[1][1]
        entity_profile = self._entity_priority(question, entity)
        if entity_profile:
            return self._result(
                entity_profile, constraints, 1.0, "rules", lexical_scores, {}, ambiguities, []
            )
        if best >= 3 and best - runner_up >= 2:
            confidence = min(0.99, 0.7 + 0.05 * (best - runner_up))
            return self._result(
                self._profile(best_id), constraints, confidence, "rules",
                lexical_scores, {}, ambiguities, [],
            )

        if not self._online_ready:
            ambiguities.append("no clear rule winner and online hybrid mapping is disabled")
            return self._result(
                OPEN_QUESTION_PROFILE, constraints, 0.0, "abstention",
                lexical_scores, {}, ambiguities, [self._disabled_trace()],
            )

        dense_scores, dense_trace = self._dense_scores(question)
        if dense_trace.status != "SUCCESS":
            ambiguities.append("dense mapping provider failed; deterministic abstention applied")
            return self._result(
                OPEN_QUESTION_PROFILE, constraints, 0.0, "abstention",
                lexical_scores, dense_scores, ambiguities, [dense_trace],
            )
        combined = {
            profile.id: 0.45 * min(1.0, lexical_scores[profile.id] / 6) +
            0.55 * max(0.0, dense_scores.get(profile.id, 0.0))
            for profile in PROFILES
        }
        hybrid_ordered = sorted(combined.items(), key=lambda item: (-item[1], item[0]))
        hybrid_id, hybrid_score = hybrid_ordered[0]
        margin = hybrid_score - hybrid_ordered[1][1]
        # A moderate absolute score with a clear margin is safer than asking a
        # stochastic judge. The thresholds are exposed and exercised in notebook 05.
        if hybrid_score >= 0.58 and margin >= 0.10:
            return self._result(
                self._profile(hybrid_id), constraints, hybrid_score, "hybrid_dense",
                lexical_scores, dense_scores, ambiguities, [dense_trace],
            )

        judge_profile, judge_trace = self._judge(question, hybrid_ordered[:3], entity, period)
        calls = [dense_trace, judge_trace]
        if judge_profile:
            return self._result(
                judge_profile, constraints, max(0.55, hybrid_score), "llm_judge",
                lexical_scores, dense_scores, ambiguities, calls,
            )
        ambiguities.append("hybrid scores remained ambiguous and judge did not validate a profile")
        return self._result(
            OPEN_QUESTION_PROFILE, constraints, hybrid_score, "abstention",
            lexical_scores, dense_scores, ambiguities, calls,
        )

    @property
    def _online_ready(self) -> bool:
        return bool(self.online_enabled and self.api_key and self.embedding_model)

    def _lexical_scores(self, question: str) -> dict[str, float]:
        tokens = set(_normalize(question).split())
        return {profile.id: float(_trigger_score(tokens, profile)[0]) for profile in PROFILES}

    def _entity_priority(self, question: str, entity: str | None) -> EvidenceProfile | None:
        tokens = set(_normalize(question).split())
        prudential = bool(tokens & {
            "scr", "solvency", "prudential", "coverage", "prudentiel", "prudentielle",
            "solvabilite", "couverture",
        })
        if entity in {"Foyer Assurances S.A.", "Foyer Global Health S.A."} and prudential:
            return self._profile("entity_prudential_coverage")
        if entity == "Foyer Global Health S.A.":
            return self._profile("international_health")
        return None

    def _dense_scores(self, question: str) -> tuple[dict[str, float], ModelCallTrace]:
        try:
            self._configure_trust_store()
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            prototype_texts = [
                f"{profile.label}. {profile.description}. "
                f"{' '.join(PROFILE_EXAMPLES[profile.id])}"
                for profile in PROFILES
            ]
            contents = [question] if self._prototype_vectors else [question, *prototype_texts]
            response = client.models.embed_content(
                model=self.embedding_model,
                contents=contents,
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
            )
            vectors = [embedding.values for embedding in response.embeddings]
            query_vector = vectors[0]
            if self._prototype_vectors is None:
                self._prototype_vectors = {
                    profile.id: vector
                    for profile, vector in zip(PROFILES, vectors[1:], strict=True)
                }
            scores = {
                profile_id: self._cosine(query_vector, vector)
                for profile_id, vector in self._prototype_vectors.items()
            }
            return scores, ModelCallTrace(
                provider="gemini", model=self.embedding_model,
                purpose="ambiguous_profile_embedding", status="SUCCESS", attempts=1,
                detail="Question and profile prototypes embedded.",
            )
        except Exception:
            return {}, ModelCallTrace(
                provider="gemini", model=self.embedding_model,
                purpose="ambiguous_profile_embedding", status="ERROR", attempts=1,
                detail="Provider failure; deterministic mapping abstained.",
            )

    def _judge(
        self,
        question: str,
        candidates: list[tuple[str, float]],
        entity: str | None,
        period: str | None,
    ) -> tuple[EvidenceProfile | None, ModelCallTrace]:
        if not self.generation_model:
            return None, self._disabled_trace("ambiguous_profile_judge")
        self._configure_trust_store()
        from google import genai
        from google.genai import types

        allowed = [profile_id for profile_id, _ in candidates]
        candidate_contracts = [
            {
                "profile_id": profile.id,
                "label": profile.label,
                "description": profile.description,
                "required_fields": [field.label for field in profile.fields],
            }
            for profile in PROFILES
            if profile.id in allowed
        ]
        prompt = (
            "Act as a conservative intent router, not an answer generator. Select a profile "
            "only when its complete evidence contract matches the user's requested information. "
            "Return JSON with profile_id and reason. Candidate contracts: "
            + json.dumps(candidate_contracts) +
            f". Question={question!r}; detected_entity={entity!r}; detected_period={period!r}. "
            "Return profile_id=null when the question is vague, spans incompatible contracts, "
            "or does not request the candidate fields."
        )
        client = genai.Client(api_key=self.api_key)
        try:
            response = client.models.generate_content(
                model=self.generation_model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            payload = json.loads(response.text or "{}")
            profile_id = payload.get("profile_id")
            profile = self._profile(profile_id) if profile_id in allowed else None
            return profile, ModelCallTrace(
                provider="gemini", model=self.generation_model,
                purpose="ambiguous_profile_judge", status="SUCCESS", attempts=1,
                detail="Structured result validated against the allowed profile IDs.",
            )
        except Exception:
            return None, ModelCallTrace(
                provider="gemini", model=self.generation_model,
                purpose="ambiguous_profile_judge", status="ERROR", attempts=1,
                detail="Provider failure; mapping abstained.",
            )

    def _result(
        self, profile: EvidenceProfile, constraints: EvidenceConstraints, confidence: float,
        source: str, lexical: dict[str, float], dense: dict[str, float],
        ambiguities: list[str], calls: list[ModelCallTrace],
    ) -> MappedQuestion:
        decision = MappingDecision(
            profile_id=profile.id, entity=constraints.entity, period=constraints.period,
            confidence=round(confidence, 4), decision_source=source,
            lexical_scores=lexical, dense_scores=dense, ambiguities=ambiguities,
            model_calls=calls,
        )
        return MappedQuestion(profile=profile, constraints=constraints, decision=decision)

    @staticmethod
    def _profile(profile_id: str) -> EvidenceProfile:
        for profile in (*PROFILES, OPEN_QUESTION_PROFILE):
            if profile.id == profile_id:
                return profile
        raise ValueError(f"Unknown evidence profile: {profile_id}")

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=True))
        denominator = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right)) or 1.0
        return numerator / denominator

    def _disabled_trace(self, purpose: str = "ambiguous_profile_embedding") -> ModelCallTrace:
        return ModelCallTrace(
            provider="gemini", model=self.embedding_model or None, purpose=purpose,
            status="DISABLED", attempts=0,
            detail="Hybrid mapping is disabled or provider configuration is incomplete.",
        )

    @staticmethod
    def _configure_trust_store() -> None:
        try:
            import truststore

            truststore.inject_into_ssl()
        except ImportError:
            pass
