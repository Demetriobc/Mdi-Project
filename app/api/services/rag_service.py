"""Só encaminha pro retriever FAISS e formata texto/fontes pro prompt."""

from __future__ import annotations

from app.api.schemas.chat import PredictionContext
from app.core.logger import get_logger
from app.rag.retriever import RetrievedChunk, retrieve_for_chat, retrieve_for_prediction, vectorstore_exists

logger = get_logger(__name__)


def get_prediction_context_chunks(context: PredictionContext) -> list[RetrievedChunk]:
    if not vectorstore_exists():
        logger.warning("Vectorstore ausente; RAG vazio.")
        return []
    try:
        return retrieve_for_prediction(
            zipcode=context.zipcode,
            predicted_price=context.predicted_price,
            grade=context.grade,
            sqft_living=context.sqft_living,
        )
    except Exception as e:
        logger.error("RAG (predição): %s", e)
        return []


def get_chat_context_chunks(
    message: str,
    context: PredictionContext | None,
) -> list[RetrievedChunk]:
    if not vectorstore_exists():
        logger.warning("Vectorstore ausente; RAG vazio.")
        return []
    try:
        z = context.zipcode if context else "98000"
        p = context.predicted_price if context else 0.0
        return retrieve_for_chat(message, z, p)
    except Exception as e:
        logger.error("RAG (chat): %s", e)
        return []


def extract_sources(chunks: list[RetrievedChunk]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for c in chunks:
        if c.source not in seen:
            seen.add(c.source)
            out.append(c.source)
    return out


def format_chunks_as_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return ""
    lines = ["=== CONTEXTO DA BASE DE CONHECIMENTO ==="]
    for i, c in enumerate(chunks, 1):
        lines.append(f"\n[Fonte {i}: {c.source}]")
        lines.append(c.content.strip())
    return "\n".join(lines)
