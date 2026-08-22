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
