from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_deep_question_is_complete_and_cited() -> None:
    response = client.post(
        "/api/query",
        json={
            "question": "Quels indicateurs publics décrivent la position du Groupe en 2025 ?",
            "mode": "deep",
            "scope": {"document_ids": ["foyer_financial_information_2025"]},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETE"
    assert payload["profile_id"] == "public_position"
    assert len(payload["claims"]) == 3
    assert not payload["missing_fields"]
    accepted_ids = {item["id"] for item in payload["evidence"] if item["state"] == "ACCEPTED"}
    assert accepted_ids
    assert all(set(claim["evidence_ids"]) <= accepted_ids for claim in payload["claims"])


def test_scope_can_force_partial_answer() -> None:
    response = client.post(
        "/api/query",
        json={
            "question": "Quels indicateurs clients sont publiés ?",
            "mode": "deep",
            "scope": {"document_ids": ["foyer_financial_information_2025"]},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "NOT_FOUND"
    assert len(payload["missing_fields"]) == 3
    assert payload["claims"] == []


def test_quick_mode_limits_visible_claims_without_faking_completeness() -> None:
    response = client.post(
        "/api/query",
        json={
            "question": "Quels chiffres clés pour Global Health ?",
            "mode": "quick",
            "scope": {"document_ids": ["foyer_annual_report_2025"]},
        },
    )
    payload = response.json()
    assert payload["status"] == "COMPLETE"
    assert payload["profile_id"] == "international_health"
    assert len(payload["claims"]) == 2
    assert all(item["state"] == "COVERED" for item in payload["coverage"])


def test_answer_contract_rejects_unknown_mode() -> None:
    response = client.post(
        "/api/query",
        json={"question": "Une question valide", "mode": "magic", "scope": {}},
    )
    assert response.status_code == 422


def test_unanswerable_question_does_not_create_false_completeness() -> None:
    response = client.post(
        "/api/query",
        json={
            "question": "Quel est le taux de rotation du personnel en 2025 ?",
            "mode": "deep",
            "scope": {"document_ids": ["foyer_annual_report_2025"]},
        },
    )
    payload = response.json()
    assert payload["profile_id"] == "open_question"
    assert payload["status"] == "NOT_FOUND"
    assert payload["claims"] == []


def test_weak_keyword_match_abstains_instead_of_switching_question() -> None:
    response = client.post(
        "/api/query",
        json={
            "question": "Combien de sinistres ont été déclarés en 2025 ?",
            "mode": "deep",
            "scope": {"document_ids": ["foyer_annual_report_2025"]},
        },
    )
    payload = response.json()
    assert payload["profile_id"] == "open_question"
    assert payload["status"] == "NOT_FOUND"
