from __future__ import annotations

import re
import unicodedata

from app.domain.models import EvidenceField, EvidenceProfile

PROFILES: tuple[EvidenceProfile, ...] = (
    EvidenceProfile(
        id="prudential_coverage",
        version="1.0.0",
        label="Couverture prudentielle du Groupe",
        description="Fonds propres éligibles, SCR total et ratio de couverture publiés.",
        triggers=["prudentielle", "solvabilite", "scr", "couverture", "fonds propres eligibles"],
        fields=[
            EvidenceField(
                id="eligible_own_funds_scr",
                label="Fonds propres éligibles couvrant le SCR total",
                value_type="currency",
                query_templates=["S.23.01 R0660 fonds propres éligibles SCR total groupe"],
            ),
            EvidenceField(
                id="group_scr",
                label="Capital de solvabilité requis total du Groupe",
                value_type="currency",
                query_templates=["S.23.01 R0680 capital solvabilité requis total groupe SCR"],
            ),
            EvidenceField(
                id="scr_coverage_ratio",
                label="Ratio de couverture du SCR total",
                value_type="percentage",
                query_templates=["S.23.01 R0690 ratio fonds propres éligibles SCR total groupe"],
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
                query_templates=["capitaux propres part du Groupe 2025", "equity group share"],
            ),
            EvidenceField(
                id="non_life_market_share",
                label="Part de marché non-vie au Luxembourg",
                value_type="percentage",
                query_templates=[
                    "part de marché assurance non-vie Luxembourg",
                    "non-life market share",
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
                query_templates=["Global Health active pays couverture internationale"],
            ),
            EvidenceField(
                id="earned_premiums",
                label="Primes acquises",
                value_type="currency",
                query_templates=["Global Health primes acquises earned premiums"],
            ),
            EvidenceField(
                id="employee_count",
                label="Effectif publié",
                value_type="integer",
                query_templates=["Global Health employés effectif"],
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


def map_question(question: str, explicit_profile_id: str | None = None) -> EvidenceProfile:
    if explicit_profile_id:
        for profile in (*PROFILES, OPEN_QUESTION_PROFILE):
            if profile.id == explicit_profile_id:
                return profile

    normalized_question = " ".join(_normalize(question))
    if "global health" in normalized_question:
        return next(profile for profile in PROFILES if profile.id == "international_health")

    question_tokens = set(normalized_question.split())
    best_profile = PROFILES[0]
    best_score = -1
    for profile in PROFILES:
        score = 0
        for trigger in profile.triggers:
            trigger_tokens = set(_normalize(trigger))
            if trigger_tokens and trigger_tokens.issubset(question_tokens):
                score += len(trigger_tokens) + 1
        if score > best_score:
            best_profile = profile
            best_score = score
    return best_profile if best_score >= 3 else OPEN_QUESTION_PROFILE


def list_profiles() -> list[EvidenceProfile]:
    return [*PROFILES, OPEN_QUESTION_PROFILE]
