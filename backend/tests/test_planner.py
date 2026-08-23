from app.domain.profiles import PROFILES
from app.retrieval.planner import plan_queries


def test_planner_exposes_bilingual_field_reformulations() -> None:
    profile = next(item for item in PROFILES if item.id == "prudential_coverage")
    queries = plan_queries("Quelle est la couverture ?", profile, ["doc"])

    assert len(queries) > len(profile.fields)
    assert {query.field_id for query in queries} == {field.id for field in profile.fields}
    assert any("fonds propres" in query.text.lower() for query in queries)
    assert any("eligible own funds" in query.text.lower() for query in queries)


def test_planner_adds_only_bounded_validated_conversation_context() -> None:
    profile = next(item for item in PROFILES if item.id == "prudential_coverage")
    queries = plan_queries(
        "Et pour le ratio ?",
        profile,
        ["doc"],
        conversation_context="Validated profile: prudential_coverage. scr: 100 EUR.",
    )

    assert all("Current question: Et pour le ratio ?" in query.text for query in queries)
    assert all("Validated profile: prudential_coverage" in query.text for query in queries)
