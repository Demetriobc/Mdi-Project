"""
Serviço de predição.

Camada de orquestração entre o endpoint HTTP e o núcleo de ML.
Responsabilidades:
- Converter o schema Pydantic para o formato do modelo
- Chamar o módulo de inferência
- Enriquecer o resultado com contexto de mercado (mediana do zipcode)
- Construir o PredictionResponse para a API

Regra: nenhuma lógica de ML vive aqui. Este serviço apenas coordena.
"""

from __future__ import annotations

from functools import lru_cache

from app.api.schemas.prediction import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    HouseInput,
    PredictionResponse,
)
from app.core.logger import get_logger
from app.ml.predict import PredictionResult, predict_batch, predict_price
from app.ml.model_registry import load_metadata, artifacts_exist

logger = get_logger(__name__)


# ── Contexto de mercado por zipcode ───────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_zipcode_stats() -> dict[str, float]:
    """
    Carrega as medianas de preço por zipcode dos metadados do modelo.

    Retorna dicionário vazio se os metadados não estiverem disponíveis.
    Os zipcode stats são derivados do dataset de treino durante `train.py`
    e armazenados em metadata.json.
    """
    if not artifacts_exist():
        return {}

    try:
        metadata = load_metadata()
        return metadata.get("zipcode_median_prices", {})
    except Exception as e:
        logger.warning(f"Não foi possível carregar zipcode stats: {e}")
        return {}


def _enrich_with_market_context(
    result: PredictionResult,
    zipcode: str,
) -> tuple[float | None, float | None]:
    """
    Busca a mediana de preço do zipcode e calcula o desvio percentual.

    Returns:
        (zipcode_median_price, price_vs_median_pct)
    """
    stats = _load_zipcode_stats()
    median = stats.get(zipcode)

    if median is None:
        return None, None

    pct_diff = ((result.predicted_price - median) / median) * 100
    return round(median, 2), round(pct_diff, 2)


# ── Conversão de resultado ────────────────────────────────────────────────────

def _to_response(result: PredictionResult) -> PredictionResponse:
    """Converte PredictionResult (ML) → PredictionResponse (API)."""
    zipcode_median, pct_diff = _enrich_with_market_context(result, result.zipcode)

    return PredictionResponse(
        predicted_price=result.predicted_price,
        predicted_price_formatted=result.predicted_price_formatted,
        zipcode=result.zipcode,
        sqft_living=result.sqft_living,
        bedrooms=result.bedrooms,
        bathrooms=result.bathrooms,
        grade=result.grade,
        condition=result.condition,
        model_version=result.model_version,
        top_features=result.top_features,
        zipcode_median_price=zipcode_median,
        price_vs_median_pct=pct_diff,
    )


# ── Interface pública do serviço ──────────────────────────────────────────────

def predict_single(house: HouseInput) -> PredictionResponse:
    """
    Executa a predição para um único imóvel.

    Args:
        house: dados validados pelo schema Pydantic

    Returns:
        PredictionResponse com preço previsto e contexto de mercado

    Raises:
        FileNotFoundError: artefatos não gerados (make train)
        ValueError: input inválido que o modelo não consegue processar
    """
    logger.info(
        f"Predição solicitada — zipcode: {house.zipcode}, "
        f"sqft: {house.sqft_living}, grade: {house.grade}"
    )

    model_input = house.to_model_input()
    result = predict_price(model_input)

    logger.info(f"Preço previsto: {result.predicted_price_formatted}")
    return _to_response(result)


def predict_many(request: BatchPredictionRequest) -> BatchPredictionResponse:
    """
    Executa predição em lote.

    Mais eficiente que múltiplas chamadas ao endpoint single para
    casos de uso como análise de portfólio ou comparação de imóveis.
    """
    logger.info(f"Predição em lote — {len(request.houses)} imóveis")

    model_inputs = [house.to_model_input() for house in request.houses]
    results = predict_batch(model_inputs)

    responses = [_to_response(r) for r in results]
    model_version = responses[0].model_version if responses else "unknown"

    logger.info(f"Lote processado: {len(responses)} previsões")

    return BatchPredictionResponse(
        predictions=responses,
        count=len(responses),
        model_version=model_version,
    )
