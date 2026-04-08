"""
Configuração de embeddings para o pipeline RAG.

Suporta dois provedores controlados pela variável EMBEDDING_PROVIDER no .env:

  local  → fastembed (BAAI/bge-small-en-v1.5, ONNX, gratuito, sem PyTorch)
  openai → OpenAI text-embedding-3-small (melhor qualidade, exige créditos)

Padrão: local — funciona imediatamente sem nenhum custo.
Troque para openai quando tiver créditos disponíveis para qualidade superior.
"""

from functools import lru_cache
from typing import Protocol

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
LOCAL_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # 33MB, rápido, boa qualidade


class EmbeddingModel(Protocol):
    """Protocol para compatibilidade entre backends de embedding."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


@lru_cache(maxsize=1)
def get_embeddings() -> EmbeddingModel:
    """
    Retorna o modelo de embeddings configurado (singleton cacheado).

    Seleciona o provider com base em EMBEDDING_PROVIDER no .env:
    - "local"  → fastembed (padrão, gratuito)
    - "openai" → OpenAI embeddings (exige OPENAI_API_KEY com créditos)
    """
    provider = getattr(settings, "embedding_provider", "local")

    if provider == "openai":
        return _get_openai_embeddings()
    else:
        return _get_local_embeddings()


def _get_local_embeddings() -> EmbeddingModel:
    """
    Embeddings locais via fastembed (ONNX).

    Vantagens: gratuito, sem API key, sem PyTorch, funciona offline.
    O modelo BAAI/bge-small-en-v1.5 (~33MB) é baixado automaticamente
    na primeira execução e cacheado localmente.
    """
    try:
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        embeddings = FastEmbedEmbeddings(model_name=LOCAL_EMBEDDING_MODEL)
        logger.info(f"Embeddings configurados: local fastembed ({LOCAL_EMBEDDING_MODEL})")
        return embeddings

    except ImportError as e:
        raise ImportError(
            f"fastembed não instalado: {e}. "
            "Execute: pip install fastembed"
        ) from e


def _get_openai_embeddings() -> EmbeddingModel:
    """Embeddings via API OpenAI (requer chave com créditos disponíveis)."""
    if not settings.has_openai_key:
        raise EnvironmentError(
            "OPENAI_API_KEY não configurada. "
            "Adicione sua chave ao .env ou use EMBEDDING_PROVIDER=local."
        )

    try:
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(
            model=OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.openai_api_key,
        )
        logger.info(f"Embeddings configurados: OpenAI {OPENAI_EMBEDDING_MODEL}")
        return embeddings

    except ImportError as e:
        raise ImportError(
            f"langchain-openai não instalado: {e}. "
            "Execute: pip install langchain-openai"
        ) from e
