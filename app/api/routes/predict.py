"""POST /predict, /predict/explain, /predict/batch."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
from app.db.crud import log_prediction
from app.db.session import get_db

router = APIRouter(prefix="/predict", tags=["prediction"])
logger = get_logger(__name__)


@router.post("", response_model=PredictionResponse)
async def predict(house: HouseInput, db: Session = Depends(get_db)) -> PredictionResponse:
    try:
        result = predict_single(house)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    except Exception as e:
        logger.error("predict: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a predicao.",
        ) from e

    log_prediction(
        db=db,
        house_input=house.to_model_input(),
        predicted_price=result.predicted_price,
        zipcode_median_price=result.zipcode_median_price,
        price_vs_median_pct=result.price_vs_median_pct,
    )
    return result


@router.post("/explain")
async def predict_with_explanation(house: HouseInput) -> dict:
    try:
        prediction = predict_single(house)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e

    ctx = PredictionContext(
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
    explanation = explanation_service.generate_initial_explanation(ctx)
    return {
        "prediction": prediction.model_dump(),
        "explanation": explanation.answer,
        "explanation_sources": explanation.sources,
        "llm_available": explanation.llm_available,
    }


@router.post("/batch", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest) -> BatchPredictionResponse:
    try:
        return predict_many(request)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    except Exception as e:
        logger.error("predict batch: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno.",
        ) from e
