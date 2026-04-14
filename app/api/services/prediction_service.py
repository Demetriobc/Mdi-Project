"""Schema Pydantic → dict → predict_price; enriquece com mediana do zip (DB ou metadata)."""

from __future__ import annotations

from functools import lru_cache

from app.api.schemas.prediction import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    HouseInput,
    PredictionResponse,
)
from app.core.logger import get_logger
from app.db.crud import get_zipcode_median
from app.db.session import db_available, get_session_factory
from app.ml.model_registry import artifacts_exist, load_metadata
from app.ml.predict import PredictionResult, predict_batch, predict_price

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _zip_median_prices_from_last_training() -> dict[str, float]:
    if not artifacts_exist():
        return {}
    try:
        return load_metadata().get("zipcode_median_prices", {})
    except Exception as e:
        logger.warning("metadata.json sem medianas de zip: %s", e)
        return {}


def median_training_price_for_zipcode(zipcode: str) -> float | None:
    if db_available():
        factory = get_session_factory()
        if factory:
            with factory() as db:
                m = get_zipcode_median(db, zipcode)
                if m is not None:
                    return m
    return _zip_median_prices_from_last_training().get(zipcode)


def pct_vs_median(predicted: float, median: float) -> float:
    return round((predicted - median) / median * 100, 2)


def prediction_result_to_response(result: PredictionResult) -> PredictionResponse:
    median = median_training_price_for_zipcode(result.zipcode)
    zipcode_median = round(median, 2) if median is not None else None
    pct = pct_vs_median(result.predicted_price, median) if median is not None else None

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
        price_vs_median_pct=pct,
        price_p10=result.price_p10,
        price_p90=result.price_p90,
    )


def predict_single(house: HouseInput) -> PredictionResponse:
    logger.info(
        "Predição zip=%s sqft=%s grade=%s",
        house.zipcode,
        house.sqft_living,
        house.grade,
    )
    raw = predict_price(house.to_model_input())
    logger.info("Preço: %s", raw.predicted_price_formatted)
    return prediction_result_to_response(raw)


def predict_many(request: BatchPredictionRequest) -> BatchPredictionResponse:
    logger.info("Lote: %s imóveis", len(request.houses))
    rows = [h.to_model_input() for h in request.houses]
    results = predict_batch(rows)
    responses = [prediction_result_to_response(r) for r in results]
    ver = responses[0].model_version if responses else "unknown"
    return BatchPredictionResponse(predictions=responses, count=len(responses), model_version=ver)
