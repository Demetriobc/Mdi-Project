"""
Avaliação de modelos de regressão.

Calcula métricas padrão para previsão de preços e extrai importância
de features para alimentar tanto os metadados do modelo quanto a camada
de explicação via SHAP.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RegressionMetrics:
    """Métricas de avaliação de um modelo de regressão."""

    rmse: float
    mae: float
    r2: float
    mape: float        # Mean Absolute Percentage Error
    median_ae: float   # Mediana do erro absoluto (robusta a outliers)

    def to_dict(self) -> dict[str, float]:
        return {k: round(v, 4) for k, v in asdict(self).items()}

    def __str__(self) -> str:
        return (
            f"RMSE: ${self.rmse:,.0f} | "
            f"MAE: ${self.mae:,.0f} | "
            f"R²: {self.r2:.4f} | "
            f"MAPE: {self.mape:.2f}%"
        )


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    log_transformed: bool = True,
) -> RegressionMetrics:
    """
    Calcula métricas de regressão no espaço original de preços (US$).

    Args:
        y_true: valores reais (em log se log_transformed=True)
        y_pred: valores previstos (em log se log_transformed=True)
        log_transformed: se True, aplica np.expm1 antes de calcular métricas
    """
    if log_transformed:
        y_true = np.expm1(y_true)
        y_pred = np.expm1(y_pred)

    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    mape = float(np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100)
    median_ae = float(np.median(np.abs(y_true - y_pred)))

    return RegressionMetrics(rmse=rmse, mae=mae, r2=r2, mape=mape, median_ae=median_ae)


def compute_feature_importance(
    model: Any,
    feature_names: list[str],
    top_n: int = 20,
) -> dict[str, float]:
    """
    Extrai importância de features via `feature_importances_` do XGBoost.

    Retorna um dicionário ordenado por importância decrescente.
    """
    if not hasattr(model, "feature_importances_"):
        logger.warning("Modelo não possui `feature_importances_`. Pulando.")
        return {}

    importance = dict(zip(feature_names, model.feature_importances_.tolist()))
    sorted_importance = dict(
        sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
    )
    return {k: round(v, 6) for k, v in sorted_importance.items()}


def compute_shap_importance(
    model: Any,
    X_sample: np.ndarray,
    feature_names: list[str],
    max_samples: int = 500,
) -> dict[str, float]:
    """
    Calcula importância média de features via SHAP (|SHAP value| médio).

    Usa uma amostra do conjunto de teste para eficiência.
    Retorna dicionário ordenado por importância decrescente.
    """
    try:
        import shap

        rng = np.random.default_rng(42)
        n = min(max_samples, len(X_sample))
        idx = rng.choice(len(X_sample), size=n, replace=False)
        X_sub = X_sample[idx]

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sub)

        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        importance = dict(zip(feature_names, mean_abs_shap.tolist()))
        sorted_importance = dict(
            sorted(importance.items(), key=lambda x: x[1], reverse=True)[:20]
        )
        return {k: round(v, 6) for k, v in sorted_importance.items()}

    except Exception as e:
        logger.warning(f"SHAP não disponível ou falhou: {e}. Usando feature_importances_.")
        return compute_feature_importance(model, feature_names)


def log_evaluation_report(
    model_name: str,
    train_metrics: RegressionMetrics,
    test_metrics: RegressionMetrics,
) -> None:
    """Imprime no log um relatório comparativo treino × teste."""
    sep = "─" * 60
    logger.info(sep)
    logger.info(f"Avaliação — {model_name}")
    logger.info(sep)
    logger.info(f"  Treino : {train_metrics}")
    logger.info(f"  Teste  : {test_metrics}")
    logger.info(sep)

    overfitting_gap = train_metrics.r2 - test_metrics.r2
    if overfitting_gap > 0.05:
        logger.warning(
            f"Possível overfitting: gap de R² = {overfitting_gap:.4f} "
            "(treino vs teste)"
        )
