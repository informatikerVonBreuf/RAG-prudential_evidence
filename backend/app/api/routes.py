from __future__ import annotations

from fastapi import APIRouter

from app.domain.models import AnswerPayload, DocumentView, HealthPayload, QuestionRequest
from app.domain.profiles import list_profiles
from app.services.engine import engine
from app.store.artifacts import store

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthPayload)
def health() -> HealthPayload:
    return HealthPayload(
        corpus_version=store.corpus_version,
        documents=len(store.documents),
        chunks=len(store.chunks),
    )


@router.get("/documents", response_model=list[DocumentView])
def documents() -> list[DocumentView]:
    return store.documents


@router.get("/profiles")
def profiles() -> list[dict[str, object]]:
    return [
        {
            "id": profile.id,
            "version": profile.version,
            "label": profile.label,
            "description": profile.description,
            "fields": [
                {"id": field.id, "label": field.label, "required": field.required}
                for field in profile.fields
            ],
        }
        for profile in list_profiles()
    ]


@router.get("/suggested-questions")
def suggested_questions() -> list[dict[str, str]]:
    return [
        {
            "label": "Position du Groupe",
            "question": "Quels indicateurs publics décrivent la position du Groupe en 2025 ?",
        },
        {
            "label": "Expérience client",
            "question": "Quels indicateurs clients et opérationnels sont publiés pour 2025 ?",
        },
        {
            "label": "Global Health",
            "question": (
                "Quelle empreinte internationale et quels chiffres clés sont publiés "
                "pour Global Health ?"
            ),
        },
    ]


@router.post("/query", response_model=AnswerPayload)
async def query(request: QuestionRequest) -> AnswerPayload:
    return await engine.answer(request)
