"""
Pipeline de ingestão da knowledge base.

Lê os documentos de `data/knowledge_base/`, divide em chunks,
gera embeddings e persiste o índice FAISS em `artifacts/vectorstore/`.

Deve ser executado uma vez (ou quando os documentos forem atualizados):
    python -m app.rag.build_kb
    make build-kb

Decisão de chunking:
- Markdown: RecursiveCharacterTextSplitter com chunk_size=600, overlap=80.
  Chunks maiores preservam mais contexto; overlap evita corte no meio de
  uma explicação importante.
- CSV (zipcode_insights): cada linha é convertida em um texto descritivo
  e tratada como um chunk independente — evita misturar informações de
  zipcodes distintos num mesmo chunk.
"""

from __future__ import annotations

import csv
from pathlib import Path

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from app.core.config import settings
from app.core.logger import get_logger
from app.core.utils import ensure_dir
from app.rag.embeddings import get_embeddings

logger = get_logger(__name__)

CHUNK_SIZE = 600
CHUNK_OVERLAP = 80

# Arquivos Markdown da knowledge base
MARKDOWN_FILES = [
    "business_context.md",
    "feature_dictionary.md",
    "model_limitations.md",
    "eda_summary.md",
]

# Arquivos CSV tratados como documentos estruturados
CSV_FILES = [
    "zipcode_insights.csv",
]


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_markdown_docs(kb_path: Path) -> list[Document]:
    """Carrega arquivos Markdown e divide em chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )

    docs: list[Document] = []

    for filename in MARKDOWN_FILES:
        filepath = kb_path / filename
        if not filepath.exists():
            logger.warning(f"Arquivo não encontrado, ignorando: {filepath}")
            continue

        text = filepath.read_text(encoding="utf-8")
        chunks = splitter.create_documents(
            [text],
            metadatas=[{"source": filename, "type": "markdown"}],
        )
        docs.extend(chunks)
        logger.info(f"  {filename}: {len(chunks)} chunks")

    return docs


def _load_csv_docs(kb_path: Path) -> list[Document]:
    """
    Converte cada linha de CSV em um Document de texto descritivo.

    Formato: "Zipcode 98103 (Fremont/Wallingford, Seattle): preço mediano
    US$ 645.000, tier=high, grade médio 8. [notes]"
    """
    docs: list[Document] = []

    filepath = kb_path / "zipcode_insights.csv"
    if not filepath.exists():
        logger.warning(f"zipcode_insights.csv não encontrado: {filepath}")
        return docs

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = _zipcode_row_to_text(row)
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": "zipcode_insights.csv",
                        "type": "zipcode",
                        "zipcode": row.get("zipcode", ""),
                        "city": row.get("city", ""),
                    },
                )
            )

    logger.info(f"  zipcode_insights.csv: {len(docs)} documentos (1 por zipcode)")
    return docs


def _zipcode_row_to_text(row: dict[str, str]) -> str:
    """Formata uma linha do CSV de zipcodes como texto legível para embedding."""
    price = int(row.get("median_price_usd", 0))
    return (
        f"Zipcode {row['zipcode']} ({row['neighborhood']}, {row['city']}): "
        f"preço mediano US$ {price:,}, "
        f"faixa de mercado={row['price_tier']}, "
        f"grade médio={row['avg_grade']}. "
        f"{row.get('notes', '')}"
    )


# ── Pipeline principal ────────────────────────────────────────────────────────

def build_knowledge_base(
    kb_path: Path | None = None,
    vectorstore_path: Path | None = None,
) -> None:
    """
    Executa o pipeline completo de ingestão:
    1. Carrega e chunkiza os documentos
    2. Gera embeddings via OpenAI
    3. Persiste o índice FAISS em disco

    Args:
        kb_path: diretório da knowledge base (default: settings)
        vectorstore_path: onde salvar o FAISS index (default: settings)
    """
    kb_dir = kb_path or settings.knowledge_base_path
    vs_dir = vectorstore_path or settings.vectorstore_path

    logger.info("=" * 55)
    logger.info("Construindo knowledge base")
    logger.info("=" * 55)
    logger.info(f"KB source : {kb_dir}")
    logger.info(f"Vectorstore: {vs_dir}")

    # 1. Carregar documentos
    logger.info("\nCarregando documentos:")
    markdown_docs = _load_markdown_docs(kb_dir)
    csv_docs = _load_csv_docs(kb_dir)
    all_docs = markdown_docs + csv_docs

    if not all_docs:
        raise ValueError(
            f"Nenhum documento encontrado em {kb_dir}. "
            "Verifique se os arquivos da knowledge base existem."
        )

    logger.info(f"\nTotal: {len(all_docs)} chunks para indexar")

    # 2. Gerar embeddings e indexar
    logger.info(f"\nGerando embeddings ({getattr(settings, 'embedding_provider', 'local')})...")
    embeddings = get_embeddings()

    vectorstore = FAISS.from_documents(all_docs, embeddings)
    logger.info(f"Indice FAISS criado com {vectorstore.index.ntotal} vetores")

    # 3. Persistir
    ensure_dir(vs_dir)
    vectorstore.save_local(str(vs_dir))
    logger.info(f"\nVectorstore salvo com sucesso em: {vs_dir}")


if __name__ == "__main__":
    build_knowledge_base()
