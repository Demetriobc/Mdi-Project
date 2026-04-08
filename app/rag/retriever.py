"""
Retriever RAG sobre o índice FAISS.

Responsabilidade única: dado um contexto de predição e/ou pergunta do usuário,
recuperar os trechos mais relevantes da knowledge base.

O retriever NÃO prevê preço. NÃO chama o LLM. Apenas recupera contexto.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from langchain_community.vectorstores import FAISS

from app.core.config import settings
from app.core.logger import get_logger
from app.rag.embeddings import get_embeddings

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    """Trecho recuperado da knowledge base com metadados."""

    content: str
    source: str
    chunk_type: str        # "markdown" ou "zipcode"
    relevance_score: float  # distância L2 invertida — menor = mais relevante
    zipcode: str | None = None


# ── Carregamento do vectorstore ───────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_vectorstore() -> FAISS:
    """
    Carrega o índice FAISS do disco (singleton cacheado).

    Raises:
        FileNotFoundError: se o vectorstore não foi gerado (make build-kb).
    """
    vs_path = settings.vectorstore_path

    if not vs_path.exists():
        raise FileNotFoundError(
            f"Vectorstore não encontrado em: {vs_path}\n"
            "Execute `make build-kb` para gerar o índice RAG."
        )

    embeddings = get_embeddings()
    vectorstore = FAISS.load_local(
        str(vs_path),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    logger.info(f"Vectorstore carregado: {vectorstore.index.ntotal} vetores")
    return vectorstore


def vectorstore_exists() -> bool:
    """Verifica se o índice FAISS existe em disco."""
    return settings.vectorstore_path.exists()


# ── Funções de retrieval ──────────────────────────────────────────────────────

def retrieve(query: str, k: int | None = None) -> list[RetrievedChunk]:
    """
    Recupera os k trechos mais relevantes para a query.

    Args:
        query: texto da busca semântica
        k: número de trechos a retornar (default: settings.rag_top_k)

    Returns:
        Lista de RetrievedChunk ordenados por relevância
    """
    top_k = k or settings.rag_top_k
    vectorstore = _load_vectorstore()

    results = vectorstore.similarity_search_with_score(query, k=top_k)

    chunks = []
    for doc, score in results:
        chunks.append(
            RetrievedChunk(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                chunk_type=doc.metadata.get("type", "unknown"),
                relevance_score=float(score),
                zipcode=doc.metadata.get("zipcode"),
            )
        )

    logger.debug(f"RAG retrieved {len(chunks)} chunks para query: '{query[:60]}...'")
    return chunks


def retrieve_for_prediction(
    zipcode: str,
    predicted_price: float,
    grade: int,
    sqft_living: int,
    extra_context: str = "",
) -> list[RetrievedChunk]:
    """
    Constrói automaticamente a query de retrieval a partir do resultado
    de uma predição e recupera contexto relevante.

    Combina informações do imóvel com uma query semântica para maximizar
    a relevância dos trechos recuperados.
    """
    query_parts = [
        f"zipcode {zipcode}",
        f"preço {_price_range_label(predicted_price)}",
        f"grade {grade} qualidade construção",
        f"área {sqft_living} sqft",
    ]

    if extra_context:
        query_parts.append(extra_context)

    query = " | ".join(query_parts)
    logger.debug(f"Query RAG automática: {query}")

    # Recupera mais chunks e combina tipos diferentes para variedade
    all_chunks = retrieve(query, k=settings.rag_top_k + 2)

    # Garante ao menos 1 chunk do tipo zipcode se disponível
    has_zipcode_chunk = any(c.chunk_type == "zipcode" for c in all_chunks)
    if not has_zipcode_chunk:
        zipcode_chunks = retrieve(f"zipcode {zipcode} bairro preço mercado", k=2)
        zipcode_only = [c for c in zipcode_chunks if c.chunk_type == "zipcode"]
        if zipcode_only:
            all_chunks = zipcode_only[:1] + all_chunks[: settings.rag_top_k - 1]

    return all_chunks[: settings.rag_top_k]


def retrieve_for_chat(
    user_question: str,
    zipcode: str,
    predicted_price: float,
) -> list[RetrievedChunk]:
    """
    Retrieval orientado a uma pergunta do usuário no chat.

    Combina a pergunta direta com contexto da predição para recuperar
    trechos que respondam à pergunta dentro do contexto do imóvel específico.
    """
    augmented_query = (
        f"{user_question} | "
        f"zipcode {zipcode} | "
        f"preço {_price_range_label(predicted_price)}"
    )
    return retrieve(augmented_query, k=settings.rag_top_k)


# ── Utilitários ───────────────────────────────────────────────────────────────

def _price_range_label(price: float) -> str:
    """Converte um preço em rótulo de faixa para enriquecer a query."""
    if price < 300_000:
        return "baixo abaixo 300k acessível"
    elif price < 500_000:
        return "médio entre 300k e 500k"
    elif price < 800_000:
        return "médio-alto entre 500k e 800k"
    elif price < 1_500_000:
        return "alto acima 800k premium"
    else:
        return "luxo acima 1.5M"
