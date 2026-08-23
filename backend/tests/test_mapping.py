import pytest
from app.domain.mapping import (
    HybridQuestionMapper,
    canonicalize_entity,
    extract_entity,
    extract_period,
)
from app.domain.models import EvidenceConstraints


def test_known_entity_alias_and_period_are_extracted_without_model_call() -> None:
    mapper = HybridQuestionMapper()
    mapped = mapper.map("What was FGH solvency coverage in 2025?")

    assert mapped.profile.id == "entity_prudential_coverage"
    assert mapped.constraints.entity == "Foyer Global Health S.A."
    assert mapped.constraints.period == "2025"
    assert mapped.decision.decision_source == "rules"
    assert mapped.decision.model_calls == []


def test_french_group_prudential_question_maps_deterministically() -> None:
    mapper = HybridQuestionMapper()
    mapper.online_enabled = False
    mapped = mapper.map(
        "Quels éléments publics caractérisent la couverture prudentielle "
        "du Groupe Foyer en 2025 ?"
    )

    assert mapped.profile.id == "prudential_coverage"
    assert mapped.constraints.entity == "Groupe Foyer"
    assert mapped.constraints.period == "2025"
    assert mapped.decision.decision_source == "rules"
    assert mapped.decision.lexical_scores["prudential_coverage"] > mapped.decision.lexical_scores[
        "public_position"
    ]


def test_explicit_constraints_override_question_extraction() -> None:
    mapper = HybridQuestionMapper()
    mapped = mapper.map(
        "What was Foyer Assurances solvency coverage in 2024?",
        explicit_constraints=EvidenceConstraints(
            entity="Foyer Assurances S.A.", period="2025"
        ),
    )

    assert mapped.constraints.period == "2025"
    assert mapped.constraints.entity == "Foyer Assurances S.A."


def test_unclear_question_abstains_offline_instead_of_guessing(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_HYBRID_MAPPING", "0")
    mapper = HybridQuestionMapper()
    mapped = mapper.map("How resilient is the organisation?")

    assert mapped.profile.id == "open_question"
    assert mapped.decision.decision_source == "abstention"
    assert mapped.decision.model_calls[0].status == "DISABLED"


def test_multiple_entities_and_periods_are_reported_as_ambiguous() -> None:
    entity, entity_notes = extract_entity("Compare Foyer Assurances with Global Health")
    period, period_notes = extract_period("Compare 2024 with 2025")

    assert entity is None
    assert entity_notes
    assert period is None
    assert period_notes


def test_entity_aliases_share_one_canonical_identity() -> None:
    assert canonicalize_entity("Global Health") == "Foyer Global Health S.A."
    assert canonicalize_entity("FGH") == "Foyer Global Health S.A."


def test_identical_mapping_is_returned_from_in_memory_cache() -> None:
    mapper = HybridQuestionMapper()
    first = mapper.map("What is FGH SCR coverage in 2025?")
    second = mapper.map("What is FGH SCR coverage in 2025?")

    assert first is second


def test_multi_entity_question_abstains_without_explicit_constraint() -> None:
    mapped = HybridQuestionMapper().map(
        "Compare Foyer Assurances SCR with Global Health SCR in 2025"
    )

    assert mapped.profile.id == "open_question"
    assert mapped.decision.decision_source == "abstention"
    assert mapped.decision.ambiguities


def test_multi_period_question_abstains_without_explicit_constraint() -> None:
    mapped = HybridQuestionMapper().map("Compare Groupe Foyer coverage in 2024 and 2025")

    assert mapped.profile.id == "open_question"
    assert mapped.decision.decision_source == "abstention"


def test_french_legal_entity_prudential_wording_has_priority() -> None:
    mapped = HybridQuestionMapper().map(
        "Analyse la couverture prudentielle de Foyer Global Health en 2025."
    )

    assert mapped.profile.id == "entity_prudential_coverage"
    assert mapped.constraints.entity == "Foyer Global Health S.A."


def test_bilingual_profiles_expose_complete_metadata() -> None:
    from app.domain.profiles import list_profiles

    for profile in list_profiles():
        assert profile.label and profile.label_en
        assert profile.description and profile.description_en
        for field in profile.fields:
            assert field.label and field.label_en
            assert len(field.query_templates) >= 2


@pytest.mark.parametrize(
    ("question", "expected_profile"),
    [
        (
            "Quel est le ratio de couverture SCR du Groupe Foyer en 2025 ?",
            "prudential_coverage",
        ),
        (
            "Quel est le niveau de couverture SCR de Foyer Assurances en 2025 ?",
            "entity_prudential_coverage",
        ),
        ("What is Foyer Global Health SCR coverage in 2025?", "entity_prudential_coverage"),
        (
            "Présente une synthèse structurée de la couverture prudentielle "
            "du Groupe Foyer en 2025.",
            "prudential_coverage",
        ),
        (
            "Résume la position de solvabilité publiée par Foyer Assurances en 2025.",
            "entity_prudential_coverage",
        ),
        (
            "Summarise Foyer Global Health's published solvency position for 2025.",
            "entity_prudential_coverage",
        ),
    ],
)
def test_recruiter_ui_examples_map_deterministically(
    question: str, expected_profile: str
) -> None:
    mapped = HybridQuestionMapper().map(question)

    assert mapped.profile.id == expected_profile
    assert mapped.decision.decision_source == "rules"
