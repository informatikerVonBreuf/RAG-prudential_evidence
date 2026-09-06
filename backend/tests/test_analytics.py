from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_sql_comparison_is_exhaustive_and_source_linked() -> None:
    response = client.post(
        "/api/query",
        json={
            "question": "Compare les ratios de couverture SCR des trois entités en 2025",
            "mode": "deep",
            "scope": {
                "document_ids": [
                    "foyer_group_qrt_2025",
                    "foyer_assurances_qrt_2025",
                    "foyer_global_health_qrt_2025",
                ]
            },
            "constraints": {"period": "2025"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETE"
    assert payload["retrieval_run"]["strategy"] == "sql_analytics"
    assert payload["analytical_trace"]["route"] == "sql"
    assert payload["analytical_trace"]["row_count"] == 3
    assert "?" in payload["analytical_trace"]["sql"]
    assert all(item["source"]["row"] in {"R0690", "R0620"} for item in payload["evidence"])


def test_sql_highest_and_average_use_allow_listed_operations() -> None:
    scope = {
        "document_ids": [
            "foyer_group_qrt_2025",
            "foyer_assurances_qrt_2025",
            "foyer_global_health_qrt_2025",
        ]
    }
    highest = client.post(
        "/api/query",
        json={
            "question": "Quelle entité a le ratio de couverture SCR le plus élevé ?",
            "scope": scope,
        },
    ).json()
    average = client.post(
        "/api/query",
        json={
            "question": "Quelle est la moyenne des ratios de couverture SCR ?",
            "scope": scope,
        },
    ).json()
    assert highest["analytical_trace"]["row_count"] == 1
    assert highest["evidence"][0]["fact"]["entity"] == "Groupe Foyer"
    assert average["analytical_trace"]["row_count"] == 3
    assert "259.7 %" in average["summary"]


def test_sql_scope_and_period_are_enforced() -> None:
    payload = client.post(
        "/api/query",
        json={
            "question": "Compare les ratios de couverture SCR en 2024",
            "scope": {"document_ids": ["foyer_group_qrt_2025"]},
            "constraints": {"period": "2024"},
        },
    ).json()
    assert payload["status"] == "NOT_FOUND"
    assert payload["analytical_trace"]["row_count"] == 0


def test_mixed_question_keeps_sql_facts_and_narrative_context_separate() -> None:
    payload = client.post(
        "/api/query",
        json={
            "question": (
                "Quelle entité a le ratio de couverture SCR le plus élevé "
                "et quel contexte explique son activité ?"
            ),
            "scope": {
                "document_ids": [
                    "foyer_group_qrt_2025",
                    "foyer_assurances_qrt_2025",
                    "foyer_global_health_qrt_2025",
                    "foyer_sfcr_2025",
                    "foyer_sustainability_statement",
                    "foyer_governance_charter_2025",
                ]
            },
        },
    ).json()
    assert payload["analytical_trace"]["route"] == "sql_plus_rag"
    assert payload["evidence"][0]["fact"]["entity"] == "Groupe Foyer"
    assert payload["narrative_context"]
    assert all(item["source"]["document_id"] != "" for item in payload["narrative_context"])
