"""Rota de health check."""

from fastapi import APIRouter

from app.core.config import settings
from app.db.crud import get_prediction_stats
from app.db.session import db_available, get_session_factory
from app.ml.model_registry import artifacts_exist
from app.rag.retriever import vectorstore_exists

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """
    Verifica o status dos componentes principais do sistema.

    """
    model_ready = artifacts_exist()
    rag_ready = vectorstore_exists()
    llm_ready = settings.has_openai_key
    db_ready = db_available()

    overall = "ok" if model_ready else "degraded"

    # Estatísticas do banco (se disponível)
    db_stats = {}
    if db_ready:
        factory = get_session_factory()
        if factory:
            with factory() as db:
                db_stats = get_prediction_stats(db)

    return {
        "status": overall,
        "version": settings.app_version,
        "components": {
            "ml_model": "ready" if model_ready else "not_trained",
            "rag_vectorstore": "ready" if rag_ready else "not_built",
            "llm": "ready" if llm_ready else "no_api_key",
            "database": "connected" if db_ready else "not_configured",
        },
        "stats": db_stats,
    }
