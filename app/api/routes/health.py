"""Rota de health check."""

from fastapi import APIRouter

from app.core.config import settings
from app.ml.model_registry import artifacts_exist
from app.rag.retriever import vectorstore_exists

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """
    Verifica o status dos componentes principais do sistema.

    Útil para Railway health check e monitoramento.
    """
    model_ready = artifacts_exist()
    rag_ready = vectorstore_exists()
    llm_ready = settings.has_openai_key

    overall = "ok" if model_ready else "degraded"

    return {
        "status": overall,
        "version": settings.app_version,
        "components": {
            "ml_model": "ready" if model_ready else "not_trained",
            "rag_vectorstore": "ready" if rag_ready else "not_built",
            "llm": "ready" if llm_ready else "no_api_key",
        },
    }
