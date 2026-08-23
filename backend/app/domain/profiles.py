from __future__ import annotations

import re
import unicodedata

from app.domain.models import EvidenceField, EvidenceProfile

PROFILES: tuple[EvidenceProfile, ...] = (
    EvidenceProfile(
        id="prudential_coverage",
        version="1.1.0",
        label="Couverture prudentielle du Groupe",
        label_en="Group prudential coverage",
        description="Fonds propres éligibles publiés, SCR du Groupe et ratio de couverture.",
        description_en="Published eligible own funds, Group SCR and coverage ratio.",
        triggers=[
            "prudential",
            "prudentiel",
            "prudentielle",
            "couverture prudentielle",
            "solvency",
            "solvabilite",
            "scr",
            "coverage",
            "ratio de couverture",
            "couverture scr",
            "eligible own funds",
            "fonds propres eligibles",
            "exigence de capital",
        ],
        fields=[
            EvidenceField(
                id="eligible_own_funds_scr",
                label="Fonds propres éligibles couvrant le SCR du Groupe",
                label_en="Eligible own funds covering the Group SCR",
                value_type="currency",
                query_templates=[
                    "S.23.01.22 R0660 C0010 eligible own funds covering total group SCR",
                    "total eligible own funds available to cover the group solvency "
                    "capital requirement",
                    "Groupe Foyer prudential resources eligible for SCR coverage in 2025",
                    "fonds propres éligibles disponibles pour couvrir le capital "
                    "de solvabilité requis du Groupe",
                ],
            ),
            EvidenceField(
                id="group_scr",
                label="Capital de solvabilité requis du Groupe",
                label_en="Group Solvency Capital Requirement",
                value_type="currency",
                query_templates=[
                    "S.23.01.22 R0680 C0010 total group Solvency Capital Requirement",
                    "Groupe Foyer total SCR amount in 2025",
                    "consolidated group prudential capital requirement",
                    "capital de solvabilité requis consolidé du Groupe Foyer",
                ],
            ),
            EvidenceField(
                id="scr_coverage_ratio",
                label="Ratio de couverture du SCR du Groupe",
                label_en="Group SCR coverage ratio",
                value_type="percentage",
                query_templates=[
                    "S.23.01.22 R0690 C0010 eligible own funds to total group SCR ratio",
                    "Groupe Foyer Solvency Capital Requirement coverage rate",
                    "consolidated SCR prudential coverage ratio in 2025",
                    "taux de couverture du capital de solvabilité requis du Groupe en 2025",
                ],
            ),
        ],
    ),
    EvidenceProfile(
        id="entity_prudential_coverage",
        version="1.1.0",
        label="Couverture prudentielle d’une entité juridique",
        label_en="Legal-entity prudential coverage",
        description="Fonds propres éligibles, SCR et ratio de couverture publiés pour une entité.",
        description_en="Published eligible own funds, SCR and coverage ratio for one legal entity.",
        triggers=[
            "entity solvency", "entity scr", "foyer assurances scr", "global health scr",
            "solvabilite entite", "couverture prudentielle entite", "ratio scr entite",
            "foyer assurances solvabilite", "global health solvabilite",
        ],
        fields=[
            EvidenceField(
                id="eligible_own_funds_scr",
                label="Fonds propres éligibles couvrant le SCR de l’entité",
                label_en="Eligible own funds covering the entity SCR",
                value_type="currency",
                query_templates=[
                    "S.23.01.01 R0540 C0010 eligible own funds covering the SCR",
                    "eligible own funds available to meet the entity solvency capital requirement",
                    "fonds propres éligibles couvrant le SCR de l’entité juridique",
                ],
            ),
            EvidenceField(
                id="entity_scr",
                label="Capital de solvabilité requis de l’entité",
                label_en="Entity Solvency Capital Requirement",
                value_type="currency",
                query_templates=[
                    "S.23.01.01 R0580 C0010 Solvency Capital Requirement",
                    "entity SCR amount at year end",
                    "montant du capital de solvabilité requis de l’entité à la clôture",
                ],
            ),
            EvidenceField(
                id="scr_coverage_ratio",
                label="Ratio de couverture du SCR de l’entité",
                label_en="Entity SCR coverage ratio",
                value_type="percentage",
                query_templates=[
                    "S.23.01.01 R0620 C0010 eligible own funds to SCR ratio",
                    "entity solvency capital requirement coverage ratio",
                    "ratio de couverture du capital de solvabilité requis de l’entité",
                ],
            ),
        ],
    ),
    EvidenceProfile(
        id="public_position",
        version="1.1.0",
        label="Position publique du Groupe",
        label_en="Group public position",
        description="Capital publié, position de marché et périmètre d'activité.",
        description_en="Published equity, market position and business scope.",
        triggers=[
            "position", "capital", "capitaux propres", "marche", "solidite",
            "activites", "groupe", "chiffres cles",
        ],
        fields=[
            EvidenceField(
                id="group_equity",
                label="Capitaux propres part du Groupe",
                label_en="Equity attributable to the Group",
                value_type="currency",
                query_templates=[
                    "capitaux propres part du Groupe Foyer en 2025",
                    "montant des fonds propres attribuables au groupe",
                    "solidité financière capitaux propres consolidés",
                    "equity attributable to Groupe Foyer",
                ],
            ),
            EvidenceField(
                id="non_life_market_share",
                label="Part de marché non-vie au Luxembourg",
                label_en="Non-life market share in Luxembourg",
                value_type="percentage",
                query_templates=[
                    "part de marché assurance non-vie Luxembourg",
                    "position concurrentielle en assurance dommages au Luxembourg",
                    "Groupe Foyer non-life insurance market share in Luxembourg",
                ],
            ),
            EvidenceField(
                id="business_areas",
                label="Domaines d'activité",
                label_en="Business areas",
                value_type="text",
                query_templates=[
                    "domaines d'activité assurance prévoyance gestion patrimoniale",
                    "Groupe Foyer insurance protection and wealth management business areas",
                ],
            ),
        ],
    ),
    EvidenceProfile(
        id="customer_operations",
        version="1.1.0",
        label="Indicateurs clients et opérations",
        label_en="Customer and operational indicators",
        description="Couverture clientèle et indicateurs de satisfaction publiés.",
        description_en="Published customer reach and satisfaction indicators.",
        triggers=[
            "client", "satisfaction", "sinistre", "myfoyer", "menages", "operations",
            "service", "indicateurs clients",
        ],
        fields=[
            EvidenceField(
                id="insured_households",
                label="Ménages assurés au Luxembourg",
                label_en="Insured households in Luxembourg",
                value_type="integer",
                query_templates=["ménages assurés Luxembourg", "insured households Luxembourg"],
            ),
            EvidenceField(
                id="myfoyer_satisfaction",
                label="Satisfaction des utilisateurs MyFoyer",
                label_en="MyFoyer user satisfaction",
                value_type="percentage",
                query_templates=[
                    "satisfaction utilisateurs application MyFoyer",
                    "MyFoyer application user satisfaction",
                ],
            ),
            EvidenceField(
                id="claims_satisfaction",
                label="Satisfaction liée à la gestion des sinistres",
                label_en="Claims-handling satisfaction",
                value_type="percentage",
                query_templates=[
                    "clients satisfaits gestion sinistre",
                    "customer satisfaction with claims handling",
                ],
            ),
        ],
    ),
    EvidenceProfile(
        id="international_health",
        version="1.1.0",
        label="Activité internationale de santé",
        label_en="International health activity",
        description="Présence internationale, primes et effectifs de Global Health.",
        description_en="Global Health international reach, premiums and workforce.",
        triggers=[
            "international", "global health", "sante", "pays", "primes", "effectif",
            "mobilite", "ipmi",
        ],
        fields=[
            EvidenceField(
                id="active_countries",
                label="Pays couverts",
                label_en="Countries covered",
                value_type="integer",
                query_templates=[
                    "Global Health nombre de pays couverts à l'international",
                    "présence géographique de l'assurance santé internationale",
                    "number of countries covered by Global Health international insurance",
                ],
            ),
            EvidenceField(
                id="earned_premiums",
                label="Primes acquises",
                label_en="Earned premiums",
                value_type="currency",
                query_templates=[
                    "Global Health montant des primes acquises",
                    "primes d'assurance santé internationale comptabilisées",
                    "Global Health earned premiums",
                ],
            ),
            EvidenceField(
                id="employee_count",
                label="Effectif publié",
                label_en="Published workforce",
                value_type="integer",
                query_templates=[
                    "Global Health nombre de salariés publié",
                    "effectif de l'activité santé internationale",
                    "Global Health published employee count",
                ],
            ),
        ],
    ),
)

OPEN_QUESTION_PROFILE = EvidenceProfile(
    id="open_question",
    version="1.1.0",
    label="Question libre non couverte",
    label_en="Unsupported open question",
    description="Profil d'abstention utilisé quand aucun contrat métier n'est suffisamment proche.",
    description_en=(
        "Abstention profile used when no business evidence contract is sufficiently close."
    ),
    triggers=[],
    fields=[
        EvidenceField(
            id="direct_answer",
            label="Réponse directe à la question",
            label_en="Direct answer to the question",
            value_type="text",
            query_templates=[
                "réponse directe explicitement documentée",
                "direct answer explicitly documented",
            ],
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
    prudential_tokens = {
        "scr", "solvency", "prudential", "coverage", "prudentiel", "prudentielle",
        "solvabilite", "couverture",
    }
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
