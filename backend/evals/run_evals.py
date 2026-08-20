from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.domain.models import QuestionRequest, ScopeSelection  # noqa: E402
from app.services.engine import engine  # noqa: E402


async def evaluate() -> dict[str, object]:
    goldens = json.loads(
        (Path(__file__).with_name("golden_questions.json")).read_text(encoding="utf-8")
    )
    results: list[dict[str, object]] = []
    total_expected_fields = 0
    total_recalled_fields = 0
    grounded_claims = 0
    total_claims = 0
    false_complete = 0

    for golden in goldens:
        answer = await engine.answer(
            QuestionRequest(
                question=golden["question"],
                mode=golden["mode"],
                scope=ScopeSelection(document_ids=golden["document_ids"]),
            )
        )
        covered = {item.field_id for item in answer.coverage if item.state == "COVERED"}
        expected_fields = set(golden["expected_fields"])
        total_expected_fields += len(expected_fields)
        total_recalled_fields += len(covered & expected_fields)
        accepted_ids = {item.id for item in answer.evidence if item.state == "ACCEPTED"}
        for claim in answer.claims:
            total_claims += 1
            grounded_claims += int(
                bool(claim.evidence_ids) and set(claim.evidence_ids) <= accepted_ids
            )
        if golden["expected_status"] != "COMPLETE" and answer.status == "COMPLETE":
            false_complete += 1
        results.append(
            {
                "id": golden["id"],
                "profile_ok": answer.profile_id == golden["expected_profile"],
                "status_ok": answer.status == golden["expected_status"],
                "expected_status": golden["expected_status"],
                "actual_status": answer.status,
                "covered_fields": sorted(covered),
            }
        )

    count = len(goldens)
    not_complete_count = sum(item["expected_status"] != "COMPLETE" for item in goldens)
    metrics = {
        "cases": count,
        "profile_accuracy": sum(result["profile_ok"] for result in results) / count,
        "status_accuracy": sum(result["status_ok"] for result in results) / count,
        "required_field_recall": (
            total_recalled_fields / total_expected_fields if total_expected_fields else 1.0
        ),
        "citation_precision": grounded_claims / total_claims if total_claims else 1.0,
        "false_completeness_rate": (
            false_complete / not_complete_count if not_complete_count else 0.0
        ),
    }
    return {"metrics": metrics, "results": results}


if __name__ == "__main__":
    report = asyncio.run(evaluate())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    metrics = report["metrics"]
    if metrics["profile_accuracy"] < 1 or metrics["status_accuracy"] < 1:
        raise SystemExit(1)
    if metrics["false_completeness_rate"] > 0:
        raise SystemExit(1)
