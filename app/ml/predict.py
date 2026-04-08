"""
Módulo de inferência reutilizável.

Esta é a interface pública do pipeline de ML para o restante do sistema.
A API, o Streamlit e os serviços de explicação devem chamar apenas
`predict_price()` — nunca acessar o modelo diretamente.

Retorna um `PredictionResult` que carrega o preço previsto e metadados
relevantes para alimentar a camada de explicação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

from app.core.logger import get_logger
from app.ml.model_registry import artifacts_exist, load_metadata, load_model, load_preprocessor

logger = get_logger(__name__)


@dataclass
class PredictionResult:
    """Resultado completo de uma predição de preço."""

    predicted_price: float
    predicted_price_formatted: str

    # Contexto da predição
    zipcode: str
    sqft_living: int
    bedrooms: int
    bathrooms: float
    grade: int
    condition: int

    # Informações do modelo
    model_version: str
    top_features: dict[str, float] = field(default_factory=dict)

    # Resumo de mercado (preenchido pelo serviço de contexto, não aqui)
    zipcode_median_price: float | None = None
    price_vs_median_pct: float | None = None

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
        }


# ── Cache dos artefatos (carregados uma vez, reutilizados) ────────────────────

@lru_cache(maxsize=1)
def _load_artifacts() -> tuple[Any, Any, dict]:
    """
    Carrega e cacheia os artefatos de modelo.

    lru_cache garante que o carregamento ocorre apenas uma vez por
    processo — evita re-leitura de disco a cada chamada de inferência.
    """
    logger.info("Carregando artefatos de modelo (primeira chamada)...")
    model = load_model()
    preprocessor = load_preprocessor()
    metadata = load_metadata()
    logger.info("Artefatos carregados e cacheados.")
    return model, preprocessor, metadata


def get_model_metadata() -> dict:
    """Retorna os metadados do modelo carregado."""
    _, _, metadata = _load_artifacts()
    return metadata


# ── Inferência ────────────────────────────────────────────────────────────────

def predict_price(input_data: dict[str, Any]) -> PredictionResult:
    """
    Realiza a predição de preço para um imóvel.

    Args:
        input_data: dicionário com as features do imóvel.
                    Deve conter as colunas originais do dataset KC.
                    Campos ausentes são tolerados (imputados pelo preprocessor).

    Returns:
        PredictionResult com preço previsto e metadados.

    Raises:
        FileNotFoundError: se os artefatos não foram gerados (make train).
        ValueError: se campos críticos estiverem ausentes.
    """
    if not artifacts_exist():
        raise FileNotFoundError(
            "Artefatos de modelo não encontrados. Execute `make train` primeiro."
        )

    model, preprocessor, metadata = _load_artifacts()

    # O modelo KC não usa a coluna `date` na inferência — usa sale_month=1 como fallback
    # (ver HousePriceFeatureEngineer.transform)
    df = pd.DataFrame([input_data])

    # O pipeline salvo é o preprocessor (feature_eng + column_transformer)
    # O modelo salvo é o XGBRegressor completo via full_pipeline
    # Usamos o full_pipeline diretamente para predição
    y_log_pred = model.predict(df)
    predicted_price = float(np.expm1(y_log_pred[0]))

    # Top features do modelo para este imóvel
    top_features = _get_top_features_for_result(metadata)

    return PredictionResult(
        predicted_price=round(predicted_price, 2),
        predicted_price_formatted=f"US$ {predicted_price:,.0f}",
        zipcode=str(input_data.get("zipcode", "N/A")),
        sqft_living=int(input_data.get("sqft_living", 0)),
        bedrooms=int(input_data.get("bedrooms", 0)),
        bathrooms=float(input_data.get("bathrooms", 0)),
        grade=int(input_data.get("grade", 7)),
        condition=int(input_data.get("condition", 3)),
        model_version=metadata.get("trained_at", "unknown")[:10],
        top_features=top_features,
    )


def predict_batch(records: list[dict[str, Any]]) -> list[PredictionResult]:
    """
    Predição em lote para múltiplos imóveis.

    Mais eficiente que chamar `predict_price` em loop para grandes volumes.
    """
    if not artifacts_exist():
        raise FileNotFoundError(
            "Artefatos de modelo não encontrados. Execute `make train` primeiro."
        )

    model, _, metadata = _load_artifacts()
    df = pd.DataFrame(records)

    y_log_pred = model.predict(df)
    prices = np.expm1(y_log_pred)

    top_features = _get_top_features_for_result(metadata)

    return [
        PredictionResult(
            predicted_price=round(float(price), 2),
            predicted_price_formatted=f"US$ {price:,.0f}",
            zipcode=str(record.get("zipcode", "N/A")),
            sqft_living=int(record.get("sqft_living", 0)),
            bedrooms=int(record.get("bedrooms", 0)),
            bathrooms=float(record.get("bathrooms", 0)),
            grade=int(record.get("grade", 7)),
            condition=int(record.get("condition", 3)),
            model_version=metadata.get("trained_at", "unknown")[:10],
            top_features=top_features,
        )
        for record, price in zip(records, prices)
    ]


# ── Auxiliares ────────────────────────────────────────────────────────────────

def _get_top_features_for_result(
    metadata: dict,
    top_n: int = 5,
) -> dict[str, float]:
    """Retorna as top N features por importância dos metadados do modelo."""
    importance = metadata.get("shap_importance") or metadata.get("feature_importance", {})
    items = list(importance.items())[:top_n]
    return dict(items)
