"""
Rota de predição de preço de imóveis.

Endpoints:
  POST /predict         → previsão pura (ML, sem LLM)
  POST /predict/explain → previsão + explicação automática (ML + RAG + LLM)
  POST /predict/batch   → predição em lote (até 100 imóveis)
"""

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.chat import PredictionContext
from app.api.schemas.prediction import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    HouseInput,
    PredictionResponse,
)
from app.api.services import explanation_service
from app.api.services.prediction_service import predict_many, predict_single
from app.core.logger import get_logger

router = APIRouter(prefix="/predict", tags=["prediction"])
logger = get_logger(__name__)


@router.post("", response_model=PredictionResponse)
async def predict(house: HouseInput) -> PredictionResponse:
    """
    Prevê o preço de um imóvel com base em suas características.

    Usa exclusivamente o modelo XGBoost — sem LLM, resposta rápida.
    """
    try:
        return predict_single(house)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Erro na predicao: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a predicao.",
        ) from e


@router.post("/explain")
async def predict_with_explanation(house: HouseInput) -> dict:
    """
    Prevê o preço e gera uma explicação em linguagem natural via LLM.

    Fluxo: ML prevê → RAG recupera contexto → LLM explica.
    Se o LLM não estiver disponível, retorna a previsão com mensagem de fallback.
    """
    try:
        prediction = predict_single(house)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e

    context = PredictionContext(
        predicted_price=prediction.predicted_price,
        predicted_price_formatted=prediction.predicted_price_formatted,
        zipcode=prediction.zipcode,
        sqft_living=prediction.sqft_living,
        bedrooms=prediction.bedrooms,
        bathrooms=prediction.bathrooms,
        grade=prediction.grade,
        condition=prediction.condition,
        top_features=prediction.top_features,
        zipcode_median_price=prediction.zipcode_median_price,
        price_vs_median_pct=prediction.price_vs_median_pct,
    )

    explanation = explanation_service.generate_initial_explanation(context)

    return {
        "prediction": prediction.model_dump(),
        "explanation": explanation.answer,
        "explanation_sources": explanation.sources,
        "llm_available": explanation.llm_available,
    }


@router.post("/batch", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest) -> BatchPredictionResponse:
    """
    Predição em lote para múltiplos imóveis (máximo 100 por requisição).
    """
    try:
        return predict_many(request)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Erro na predicao em lote: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno.") from e
