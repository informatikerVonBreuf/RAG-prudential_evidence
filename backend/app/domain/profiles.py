from __future__ import annotations

import re
import unicodedata

from app.domain.models import EvidenceField, EvidenceProfile

PROFILES: tuple[EvidenceProfile, ...] = (
    EvidenceProfile(
        id="prudential_coverage",
        version="1.0.0",
        label="Group prudential coverage",
        description="Published eligible own funds, total group SCR and coverage ratio.",
        triggers=["prudential", "solvency", "scr", "coverage", "eligible own funds"],
        fields=[
            EvidenceField(
                id="eligible_own_funds_scr",
                label="Eligible own funds covering total group SCR",
                value_type="currency",
                query_templates=[
                    "S.23.01.22 R0660 C0010 eligible own funds covering total group SCR",
                    "total eligible own funds available to cover the group solvency "
                    "capital requirement",
                    "Groupe Foyer prudential resources eligible for SCR coverage in 2025",
                ],
            ),
            EvidenceField(
                id="group_scr",
                label="Total group Solvency Capital Requirement",
                value_type="currency",
                query_templates=[
                    "S.23.01.22 R0680 C0010 total group Solvency Capital Requirement",
                    "Groupe Foyer total SCR amount in 2025",
                    "consolidated group prudential capital requirement",
                ],
            ),
            EvidenceField(
                id="scr_coverage_ratio",
                label="Total group SCR coverage ratio",
                value_type="percentage",
                query_templates=[
                    "S.23.01.22 R0690 C0010 eligible own funds to total group SCR ratio",
                    "Groupe Foyer Solvency Capital Requirement coverage rate",
                    "consolidated SCR prudential coverage ratio in 2025",
                ],
            ),
        ],
    ),
    EvidenceProfile(
        id="entity_prudential_coverage",
        version="1.0.0",
        label="Legal-entity prudential coverage",
        description="Published eligible own funds, SCR and coverage ratio for one entity.",
        triggers=["entity solvency", "entity scr", "foyer assurances scr", "global health scr"],
        fields=[
            EvidenceField(
                id="eligible_own_funds_scr",
                label="Eligible own funds covering the entity SCR",
                value_type="currency",
                query_templates=[
                    "S.23.01.01 R0540 C0010 eligible own funds covering the SCR",
                    "eligible own funds available to meet the entity solvency capital requirement",
                ],
            ),
            EvidenceField(
                id="entity_scr",
                label="Entity Solvency Capital Requirement",
                value_type="currency",
                query_templates=[
                    "S.23.01.01 R0580 C0010 Solvency Capital Requirement",
                    "entity SCR amount at year end",
                ],
            ),
            EvidenceField(
                id="scr_coverage_ratio",
                label="Entity SCR coverage ratio",
                value_type="percentage",
                query_templates=[
                    "S.23.01.01 R0620 C0010 eligible own funds to SCR ratio",
                    "entity solvency capital requirement coverage ratio",
                ],
            ),
        ],
    ),
    EvidenceProfile(
        id="public_position",
        version="1.0.0",
        label="Position publique du Groupe",
        description="Capital publié, position de marché et périmètre d'activité.",
        triggers=[
            "position", "capital", "capitaux propres", "marche", "solidite",
            "activites", "groupe", "chiffres cles",
        ],
        fields=[
            EvidenceField(
                id="group_equity",
                label="Capitaux propres part du Groupe",
                value_type="currency",
                query_templates=[
                    "capitaux propres part du Groupe Foyer en 2025",
                    "montant des fonds propres attribuables au groupe",
                    "solidité financière capitaux propres consolidés",
                ],
            ),
            EvidenceField(
                id="non_life_market_share",
                label="Part de marché non-vie au Luxembourg",
                value_type="percentage",
                query_templates=[
                    "part de marché assurance non-vie Luxembourg",
                    "position concurrentielle en assurance dommages au Luxembourg",
                ],
            ),
            EvidenceField(
                id="business_areas",
                label="Domaines d'activité",
                value_type="text",
                query_templates=["domaines d'activité assurance prévoyance gestion patrimoniale"],
            ),
        ],
    ),
    EvidenceProfile(
        id="customer_operations",
        version="1.0.0",
        label="Indicateurs clients et opérations",
        description="Couverture clientèle et indicateurs de satisfaction publiés.",
        triggers=[
            "client", "satisfaction", "sinistre", "myfoyer", "menages", "operations",
            "service", "indicateurs clients",
        ],
        fields=[
            EvidenceField(
                id="insured_households",
                label="Ménages assurés au Luxembourg",
                value_type="integer",
                query_templates=["ménages assurés Luxembourg", "insured households Luxembourg"],
            ),
            EvidenceField(
                id="myfoyer_satisfaction",
                label="Satisfaction des utilisateurs MyFoyer",
                value_type="percentage",
                query_templates=["satisfaction utilisateurs application MyFoyer"],
            ),
            EvidenceField(
                id="claims_satisfaction",
                label="Satisfaction liée à la gestion des sinistres",
                value_type="percentage",
                query_templates=["clients satisfaits gestion sinistre"],
            ),
        ],
    ),
    EvidenceProfile(
        id="international_health",
        version="1.0.0",
        label="Activité internationale de santé",
        description="Présence internationale, primes et effectifs de Global Health.",
        triggers=[
            "international", "global health", "sante", "pays", "primes", "effectif",
            "mobilite", "ipmi",
        ],
        fields=[
            EvidenceField(
                id="active_countries",
                label="Pays couverts",
                value_type="integer",
                query_templates=[
                    "Global Health nombre de pays couverts à l'international",
                    "présence géographique de l'assurance santé internationale",
                ],
            ),
            EvidenceField(
                id="earned_premiums",
                label="Primes acquises",
                value_type="currency",
                query_templates=[
                    "Global Health montant des primes acquises",
                    "primes d'assurance santé internationale comptabilisées",
                ],
            ),
            EvidenceField(
                id="employee_count",
                label="Effectif publié",
                value_type="integer",
                query_templates=[
                    "Global Health nombre de salariés publié",
                    "effectif de l'activité santé internationale",
                ],
            ),
        ],
    ),
)

OPEN_QUESTION_PROFILE = EvidenceProfile(
    id="open_question",
    version="1.0.0",
    label="Question libre non couverte",
    description="Profil d'abstention utilisé quand aucun contrat métier n'est suffisamment proche.",
    triggers=[],
    fields=[
        EvidenceField(
            id="direct_answer",
            label="Réponse directe à la question",
            value_type="text",
            query_templates=["réponse directe explicitement documentée"],
        )
    ],
)


def _normalize(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", folded)


def _trigger_score(question_tokens: set[str], profile: EvidenceProfile) -> tuple[int, list[str]]:
    matched: list[str] = []
    score = 0
    for trigger in profile.triggers:
        trigger_tokens = set(_normalize(trigger))
        if trigger_tokens and trigger_tokens.issubset(question_tokens):
            matched.append(trigger)
            score += len(trigger_tokens) + 1
    return score, matched


def explain_question_mapping(question: str) -> list[dict[str, object]]:
    """Expose deterministic profile scores for audits and notebook diagnostics."""
    question_tokens = set(_normalize(question))
    selected = map_question(question)
    rows: list[dict[str, object]] = []
    for profile in PROFILES:
        score, matched = _trigger_score(question_tokens, profile)
        rows.append(
            {
                "profile_id": profile.id,
                "matched_triggers": matched,
                "score": score,
                "selected": profile.id == selected.id,
                "selection_note": (
                    "entity-specific rule"
                    if selected.id == "entity_prudential_coverage" and profile.id == selected.id
                    else "Global Health rule"
                    if selected.id == "international_health" and profile.id == selected.id
                    else "highest trigger score (minimum 3)"
                    if profile.id == selected.id
                    else ""
                ),
            }
        )
    if selected.id == OPEN_QUESTION_PROFILE.id:
        rows.append(
            {
                "profile_id": selected.id,
                "matched_triggers": [],
                "score": 0,
                "selected": True,
                "selection_note": "no business profile reached the minimum score",
            }
        )
    return rows


def map_question(question: str, explicit_profile_id: str | None = None) -> EvidenceProfile:
    if explicit_profile_id:
        for profile in (*PROFILES, OPEN_QUESTION_PROFILE):
            if profile.id == explicit_profile_id:
                return profile

    normalized_question = " ".join(_normalize(question))
    prudential_tokens = {"scr", "solvency", "prudential", "coverage"}
    if (
        "foyer assurances" in normalized_question or "global health" in normalized_question
    ) and prudential_tokens.intersection(normalized_question.split()):
        return next(
            profile for profile in PROFILES if profile.id == "entity_prudential_coverage"
        )
    if "global health" in normalized_question:
        return next(profile for profile in PROFILES if profile.id == "international_health")

    question_tokens = set(normalized_question.split())
    best_profile = PROFILES[0]
    best_score = -1
    for profile in PROFILES:
        score, _ = _trigger_score(question_tokens, profile)
        if score > best_score:
            best_profile = profile
            best_score = score
    return best_profile if best_score >= 3 else OPEN_QUESTION_PROFILE


def list_profiles() -> list[EvidenceProfile]:
    return [*PROFILES, OPEN_QUESTION_PROFILE]
