"""Inferência: joblib em cache no processo; API/Streamlit chamam predict_house_price."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

from app.core.logger import get_logger
from app.ml.model_registry import (
    artifacts_exist,
    load_metadata,
    load_model,
    load_preprocessor,
    load_quantile_models,
)

logger = get_logger(__name__)


@dataclass
class PredictionResult:
    predicted_price: float
    predicted_price_formatted: str
    zipcode: str
    sqft_living: int
    bedrooms: int
    bathrooms: float
    grade: int
    condition: int
    model_version: str
    top_features: dict[str, float] = field(default_factory=dict)
    zipcode_median_price: float | None = None
    price_vs_median_pct: float | None = None
    price_p10: float | None = None
    price_p90: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicted_price": self.predicted_price,
            "predicted_price_formatted": self.predicted_price_formatted,
            "zipcode": self.zipcode,
            "sqft_living": self.sqft_living,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "grade": self.grade,
            "condition": self.condition,
            "model_version": self.model_version,
            "top_features": self.top_features,
            "zipcode_median_price": self.zipcode_median_price,
            "price_vs_median_pct": self.price_vs_median_pct,
            "price_p10": self.price_p10,
            "price_p90": self.price_p90,
        }


@lru_cache(maxsize=1)
def _cached_model_and_metadata() -> tuple[Any, Any, dict]:
    logger.info("Carregando modelo + metadados (1x por processo).")
    return load_model(), load_preprocessor(), load_metadata()


@lru_cache(maxsize=1)
def _cached_quantile_pipelines() -> tuple[Any | None, Any | None]:
    return load_quantile_models()


def get_model_metadata() -> dict:
    return _cached_model_and_metadata()[2]


def _first_n_importance_keys(metadata: dict, n: int = 5) -> dict[str, float]:
    imp = metadata.get("shap_importance") or metadata.get("feature_importance") or {}
    items = list(imp.items())[:n]
    return dict(items)


def predict_house_price(property_row: dict[str, Any]) -> PredictionResult:
    if not artifacts_exist():
        raise FileNotFoundError("Sem artefatos em artifacts/model/. Rode o treino antes.")

    model, _, metadata = _cached_model_and_metadata()
    q10, q90 = _cached_quantile_pipelines()
    df = pd.DataFrame([property_row])

    y_log = model.predict(df)
    price = float(np.expm1(y_log[0]))

    p10 = p90 = None
    if q10 is not None and q90 is not None:
        p10 = round(float(np.expm1(q10.predict(df)[0])), 2)
        p90 = round(float(np.expm1(q90.predict(df)[0])), 2)
        if p10 > p90:
            p10, p90 = p90, p10

    return PredictionResult(
        predicted_price=round(price, 2),
        predicted_price_formatted=f"US$ {price:,.0f}",
        zipcode=str(property_row.get("zipcode", "N/A")),
        sqft_living=int(property_row.get("sqft_living", 0)),
        bedrooms=int(property_row.get("bedrooms", 0)),
        bathrooms=float(property_row.get("bathrooms", 0)),
        grade=int(property_row.get("grade", 7)),
        condition=int(property_row.get("condition", 3)),
        model_version=str(metadata.get("trained_at", "unknown"))[:10],
        top_features=_first_n_importance_keys(metadata),
        price_p10=p10,
        price_p90=p90,
    )


def predict_house_price_batch(records: list[dict[str, Any]]) -> list[PredictionResult]:
    if not artifacts_exist():
        raise FileNotFoundError("Sem artefatos em artifacts/model/. Rode o treino antes.")

    model, _, metadata = _cached_model_and_metadata()
    q10, q90 = _cached_quantile_pipelines()
    df = pd.DataFrame(records)

    prices = np.expm1(model.predict(df))
    p10_arr = np.expm1(q10.predict(df)) if q10 is not None else None
    p90_arr = np.expm1(q90.predict(df)) if q90 is not None else None
    top = _first_n_importance_keys(metadata)

    out: list[PredictionResult] = []
    for i, rec in enumerate(records):
        p10 = p90 = None
        if p10_arr is not None and p90_arr is not None:
            p10 = round(float(p10_arr[i]), 2)
            p90 = round(float(p90_arr[i]), 2)
            if p10 > p90:
                p10, p90 = p90, p10
        pr = float(prices[i])
        out.append(
            PredictionResult(
                predicted_price=round(pr, 2),
                predicted_price_formatted=f"US$ {pr:,.0f}",
                zipcode=str(rec.get("zipcode", "N/A")),
                sqft_living=int(rec.get("sqft_living", 0)),
                bedrooms=int(rec.get("bedrooms", 0)),
                bathrooms=float(rec.get("bathrooms", 0)),
                grade=int(rec.get("grade", 7)),
                condition=int(rec.get("condition", 3)),
                model_version=str(metadata.get("trained_at", "unknown"))[:10],
                top_features=top,
                price_p10=p10,
                price_p90=p90,
            )
        )
    return out


# Nomes legados usados em vários módulos
def predict_price(input_data: dict[str, Any]) -> PredictionResult:
    return predict_house_price(input_data)


def predict_batch(records: list[dict[str, Any]]) -> list[PredictionResult]:
    return predict_house_price_batch(records)
