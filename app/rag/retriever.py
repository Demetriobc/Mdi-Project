"""FAISS + embeddings: similarity_search → lista de trechos (sem LLM, sem predição)."""

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
    content: str
    source: str
    chunk_type: str
    relevance_score: float
    zipcode: str | None = None


@lru_cache(maxsize=1)
def _open_faiss_index() -> FAISS:
    path = settings.vectorstore_path
    if not path.exists():
        raise FileNotFoundError(
            f"Vectorstore não encontrado: {path}. Rode o build da knowledge base."
        )
    emb = get_embeddings()
    vs = FAISS.load_local(str(path), emb, allow_dangerous_deserialization=True)
    logger.info("FAISS carregado (%s vetores)", vs.index.ntotal)
    return vs


def vectorstore_exists() -> bool:
    return settings.vectorstore_path.exists()


def price_bucket_words(price_usd: float) -> str:
    if price_usd < 300_000:
        return "baixo abaixo 300k acessível"
    if price_usd < 500_000:
        return "médio entre 300k e 500k"
    if price_usd < 800_000:
        return "médio-alto entre 500k e 800k"
    if price_usd < 1_500_000:
        return "alto acima 800k premium"
    return "luxo acima 1.5M"


def search_knowledge_base(query: str, k: int | None = None) -> list[RetrievedChunk]:
    top_k = k or settings.rag_top_k
    vs = _open_faiss_index()
    rows = vs.similarity_search_with_score(query, k=top_k)
    out: list[RetrievedChunk] = []
    for doc, score in rows:
        out.append(
            RetrievedChunk(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                chunk_type=doc.metadata.get("type", "unknown"),
                relevance_score=float(score),
                zipcode=doc.metadata.get("zipcode"),
            )
        )
    logger.debug("RAG k=%s query=%s...", len(out), query[:50])
    return out


def retrieve_for_prediction(
    zipcode: str,
    predicted_price: float,
    grade: int,
    sqft_living: int,
    extra_context: str = "",
) -> list[RetrievedChunk]:
    parts = [
        f"zipcode {zipcode}",
        f"preço {price_bucket_words(predicted_price)}",
        f"grade {grade} qualidade construção",
        f"área {sqft_living} sqft",
    ]
    if extra_context:
        parts.append(extra_context)
    query = " | ".join(parts)

    chunks = search_knowledge_base(query, k=settings.rag_top_k + 2)
    if not any(c.chunk_type == "zipcode" for c in chunks):
        extra = search_knowledge_base(f"zipcode {zipcode} bairro preço mercado", k=2)
        zip_only = [c for c in extra if c.chunk_type == "zipcode"]
        if zip_only:
            chunks = zip_only[:1] + chunks[: settings.rag_top_k - 1]
    return chunks[: settings.rag_top_k]


def retrieve_for_chat(user_question: str, zipcode: str, predicted_price: float) -> list[RetrievedChunk]:
    q = f"{user_question} | zipcode {zipcode} | preço {price_bucket_words(predicted_price)}"
    return search_knowledge_base(q, k=settings.rag_top_k)


# nome legado
def retrieve(query: str, k: int | None = None) -> list[RetrievedChunk]:
    return search_knowledge_base(query, k)
