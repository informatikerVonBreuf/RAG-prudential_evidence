from app.domain.models import AnswerStatus, Mode
from app.domain.profiles import explain_question_mapping, map_question
from app.main import app
from app.services.engine import choose_retrieval_strategy, retrieval_budget, stop_reason_for_status
from fastapi.testclient import TestClient

client = TestClient(app)


def test_all_orchestration_routes_and_stop_reasons_are_explicit() -> None:
    assert choose_retrieval_strategy(1) == "sequential_top1"
    assert choose_retrieval_strategy(3) == "batch_multi_field"
    assert stop_reason_for_status(AnswerStatus.COMPLETE) == "contract_complete"
    assert stop_reason_for_status(AnswerStatus.CONFLICT) == "conflict"
    assert stop_reason_for_status(AnswerStatus.PARTIAL) == "budget_exhausted"
    assert stop_reason_for_status(AnswerStatus.NOT_FOUND) == "budget_exhausted"
    assert retrieval_budget(Mode.QUICK) == (1, 3)
    assert retrieval_budget(Mode.DEEP) == (1, 3, 5, 8)
    assert retrieval_budget(Mode.SUMMARY) == (3, 5, 8)


def test_mapping_explanation_exposes_selected_profile_and_trigger_score() -> None:
    rows = explain_question_mapping(
        "What public evidence describes Groupe Foyer's prudential coverage in 2025?"
    )
    selected = [row for row in rows if row["selected"]]

    assert len(selected) == 1
    assert selected[0]["profile_id"] == "prudential_coverage"
    assert selected[0]["score"] >= 3
    assert "prudential" in selected[0]["matched_triggers"]


def test_solo_entity_prudential_question_uses_solo_contract() -> None:
    profile = map_question("What is Foyer Assurances SCR coverage in 2025?")
    assert profile.id == "entity_prudential_coverage"
    assert {field.id for field in profile.fields} == {
        "eligible_own_funds_scr",
        "entity_scr",
        "scr_coverage_ratio",
    }


def test_solo_entity_prudential_evidence_respects_entity_and_period() -> None:
    base_request = {
        "question": "What is Foyer Assurances SCR coverage in 2025?",
        "mode": "deep",
        "scope": {"document_ids": ["foyer_assurances_qrt_2025"]},
    }
    complete = client.post(
        "/api/query",
        json={
            **base_request,
            "constraints": {"entity": "Foyer Assurances S.A.", "period": "2025"},
        },
    ).json()
    wrong_entity = client.post(
        "/api/query",
        json={
            **base_request,
            "constraints": {"entity": "Foyer Global Health S.A.", "period": "2025"},
        },
    ).json()
    wrong_period = client.post(
        "/api/query",
        json={
            **base_request,
            "constraints": {"entity": "Foyer Assurances S.A.", "period": "2024"},
        },
    ).json()

    assert complete["status"] == "COMPLETE"
    assert wrong_entity["status"] == "NOT_FOUND"
    assert wrong_period["status"] == "NOT_FOUND"


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
    assert payload["mapping_trace"]["decision_source"] == "rules"
    assert payload["mapping_trace"]["model_calls"] == []
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


def test_unknown_document_never_expands_scope() -> None:
    response = client.post(
        "/api/query",
        json={
            "question": "Quels indicateurs publics décrivent la position du Groupe en 2025 ?",
            "scope": {"document_ids": ["document-inexistant"]},
        },
    )
    assert response.status_code == 422
    assert "document-inexistant" in response.json()["detail"]


def test_wrong_entity_is_rejected_by_evidence_contract() -> None:
    response = client.post(
        "/api/query",
        json={
            "question": "Quels indicateurs publics décrivent la position du Groupe en 2025 ?",
            "scope": {"document_ids": ["foyer_financial_information_2025"]},
            "constraints": {"entity": "Autre assureur", "period": "2025"},
        },
    )
    payload = response.json()
    assert payload["status"] == "NOT_FOUND"
    assert any(item["state"] == "REJECTED" for item in payload["evidence"])


def test_wrong_period_is_rejected_by_evidence_contract() -> None:
    response = client.post(
        "/api/query",
        json={
            "question": "Quels indicateurs publics décrivent la position du Groupe en 2024 ?",
            "scope": {"document_ids": ["foyer_financial_information_2025"]},
            "constraints": {"entity": "Groupe Foyer", "period": "2024"},
            "profile_id": "public_position",
        },
    )
    payload = response.json()
    assert payload["status"] == "NOT_FOUND"
    assert all(item["state"] != "ACCEPTED" for item in payload["evidence"])


def test_real_qrt_coverage_contract_is_complete_and_cell_cited() -> None:
    response = client.post(
        "/api/query",
        json={
            "question": (
                "What public evidence describes Groupe Foyer's prudential coverage in 2025?"
            ),
            "scope": {"document_ids": ["foyer_group_qrt_2025"]},
            "constraints": {"entity": "Groupe Foyer", "period": "2025"},
        },
    )
    payload = response.json()
    assert payload["status"] == "COMPLETE"
    assert payload["profile_id"] == "prudential_coverage"
    # A configured provider can still fail transiently. The response must disclose
    # the deterministic fallback rather than turn a provider outage into a false failure.
    assert payload["retrieval_run"]["dense_provider"].startswith("gemini")
    assert payload["retrieval_run"]["strategy"] == "batch_multi_field"
    assert payload["retrieval_run"]["stop_reason"] == "contract_complete"
    accepted = [item for item in payload["evidence"] if item["state"] == "ACCEPTED"]
    assert {item["source"]["row"] for item in accepted} == {"R0660", "R0680", "R0690"}
    assert all(item["source"]["column"] == "C0010" for item in accepted)
    assert payload["model_calls"][0]["provider"] == "gemini"
    assert payload["model_calls"][0]["status"] == "DISABLED"
    assert payload["generation_provider"] == "deterministic"
