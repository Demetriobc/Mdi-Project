"""
Serviço RAG.

Camada fina entre as rotas/serviços e o módulo de retrieval.
Traduz os schemas da API para as chamadas do retriever e formata
os chunks recuperados em dados úteis para o LLM e para o cliente.
"""

from __future__ import annotations

from app.api.schemas.chat import PredictionContext
from app.core.logger import get_logger
from app.rag.retriever import RetrievedChunk, retrieve_for_chat, retrieve_for_prediction
from app.rag.retriever import vectorstore_exists

logger = get_logger(__name__)


def get_prediction_context_chunks(
    context: PredictionContext,
) -> list[RetrievedChunk]:
    """
    Recupera chunks relevantes para explicar uma predição.

    Usado pelo explanation_service logo após uma predição ser feita.
    """
    if not vectorstore_exists():
        logger.warning("Vectorstore nao encontrado. RAG desabilitado.")
        return []

    try:
        return retrieve_for_prediction(
            zipcode=context.zipcode,
            predicted_price=context.predicted_price,
            grade=context.grade,
            sqft_living=context.sqft_living,
        )
    except Exception as e:
        logger.error(f"Erro no RAG (predicao): {e}")
        return []


def get_chat_context_chunks(
    message: str,
    context: PredictionContext | None,
) -> list[RetrievedChunk]:
    """
    Recupera chunks relevantes para responder uma pergunta do chat.
    """
    if not vectorstore_exists():
        logger.warning("Vectorstore nao encontrado. RAG desabilitado.")
        return []

    try:
        zipcode = context.zipcode if context else "98000"
        price = context.predicted_price if context else 0.0
        return retrieve_for_chat(message, zipcode, price)
    except Exception as e:
        logger.error(f"Erro no RAG (chat): {e}")
        return []


def extract_sources(chunks: list[RetrievedChunk]) -> list[str]:
    """Extrai lista única de fontes dos chunks recuperados."""
    seen: set[str] = set()
    sources = []
    for chunk in chunks:
        if chunk.source not in seen:
            seen.add(chunk.source)
            sources.append(chunk.source)
    return sources


def format_chunks_as_context(chunks: list[RetrievedChunk]) -> str:
    """Formata chunks como bloco de texto para o prompt."""
    if not chunks:
        return ""

    lines = ["=== CONTEXTO DA BASE DE CONHECIMENTO ==="]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n[Fonte {i}: {chunk.source}]")
        lines.append(chunk.content.strip())
    return "\n".join(lines)
