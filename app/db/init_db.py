"""
Inicialização do banco de dados.

Responsabilidades:
1. Criar todas as tabelas (idempotente via CREATE IF NOT EXISTS)
2. Popular zipcode_stats com dados de duas fontes:
   - artifacts/model/metadata.json  → medianas reais do dataset de treino
   - data/knowledge_base/zipcode_insights.csv → contexto qualitativo

Executado automaticamente no startup da API.
Pode ser executado manualmente:
    python -m app.db.init_db
"""

from __future__ import annotations

import csv
from pathlib import Path

from app.core.config import settings
from app.core.logger import get_logger
from app.core.utils import load_json
from app.db.models import Base
from app.db.session import get_engine, get_session_factory

logger = get_logger(__name__)


def create_tables() -> bool:
    """
    Cria todas as tabelas no banco se não existirem.

    Retorna True se bem-sucedido, False se o banco não estiver disponível.
    """
    engine = get_engine()
    if engine is None:
        logger.warning("Banco nao configurado. Tabelas nao criadas.")
        return False

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas verificadas/criadas com sucesso.")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")
        return False


def seed_zipcode_stats() -> int:
    """
    Popula a tabela zipcode_stats com dados do modelo e da knowledge base.

    Merge entre:
    - metadata.json (medianas calculadas do treino — fonte de verdade para preços)
    - zipcode_insights.csv (cidade, bairro, tier, grade médio, notas)

    Retorna o número de zipcodes inseridos/atualizados.
    """
    factory = get_session_factory()
    if factory is None:
        return 0

    # 1. Carrega medianas do modelo (fonte primária)
    median_prices: dict[str, float] = {}
    if settings.metadata_path.exists():
        try:
            metadata = load_json(settings.metadata_path)
            median_prices = {
                str(z): float(p)
                for z, p in metadata.get("zipcode_median_prices", {}).items()
            }
            logger.info(f"Medianas carregadas: {len(median_prices)} zipcodes")
        except Exception as e:
            logger.warning(f"Nao foi possivel carregar metadata.json: {e}")

    # 2. Carrega contexto qualitativo do CSV
    kb_rows: dict[str, dict] = {}
    kb_path = settings.knowledge_base_path / "zipcode_insights.csv"
    if kb_path.exists():
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    kb_rows[row["zipcode"]] = row
            logger.info(f"KB zipcodes carregados: {len(kb_rows)} registros")
        except Exception as e:
            logger.warning(f"Nao foi possivel carregar zipcode_insights.csv: {e}")

    if not median_prices and not kb_rows:
        logger.warning("Nenhum dado de zipcode disponivel para seed.")
        return 0

    # 3. Merge e upsert
    from app.db.crud import upsert_zipcode_stats

    all_zipcodes = set(median_prices.keys()) | set(kb_rows.keys())
    count = 0

    with factory() as db:
        for zipcode in sorted(all_zipcodes):
            kb = kb_rows.get(zipcode, {})
            median = median_prices.get(zipcode) or (
                float(kb["median_price_usd"]) if "median_price_usd" in kb else None
            )

            if median is None:
                continue

            upsert_zipcode_stats(
                db=db,
                zipcode=zipcode,
                median_price=median,
                city=kb.get("city"),
                neighborhood=kb.get("neighborhood"),
                price_tier=kb.get("price_tier"),
                avg_grade=float(kb["avg_grade"]) if kb.get("avg_grade") else None,
                notes=kb.get("notes"),
            )
            count += 1

        db.commit()

    logger.info(f"Seed concluido: {count} zipcodes inseridos/atualizados.")
    return count


def init_db() -> None:
    """
    Executa a inicialização completa do banco.
    Chamada no startup da API.
    """
    ok = create_tables()
    if ok:
        seed_zipcode_stats()


if __name__ == "__main__":
    init_db()
