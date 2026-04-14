"""Métricas em US$, importância de features e SHAP opcional."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RegressionMetrics:
    rmse: float
    mae: float
    r2: float
    mape: float
    median_ae: float

    def to_dict(self) -> dict[str, float]:
        return {k: round(v, 4) for k, v in asdict(self).items()}

    def __str__(self) -> str:
        return (
            f"RMSE: ${self.rmse:,.0f} | MAE: ${self.mae:,.0f} | "
            f"R²: {self.r2:.4f} | MAPE: {self.mape:.2f}%"
        )


def dollar_space_regression_metrics(
    y_true_log: np.ndarray,
    y_pred_log: np.ndarray,
) -> RegressionMetrics:
    """y_true / y_pred no espaço log1p; métricas calculadas em dólares (expm1)."""
    y_true = np.expm1(y_true_log)
    y_pred = np.expm1(y_pred_log)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    mape = float(np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100)
    median_ae = float(np.median(np.abs(y_true - y_pred)))
    return RegressionMetrics(rmse=rmse, mae=mae, r2=r2, mape=mape, median_ae=median_ae)


def xgboost_gain_importance_top(
    model: Any,
    feature_names: list[str],
    top_n: int = 20,
) -> dict[str, float]:
    if not hasattr(model, "feature_importances_"):
        logger.warning("Modelo sem feature_importances_; importância vazia.")
        return {}
    pairs = list(zip(feature_names, model.feature_importances_.tolist()))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return {k: round(v, 6) for k, v in pairs[:top_n]}


def mean_abs_shap_importance_top(
    model: Any,
    X_sample: np.ndarray,
    feature_names: list[str],
    max_samples: int = 500,
) -> dict[str, float]:
    try:
        import shap

        rng = np.random.default_rng(42)
        n = min(max_samples, len(X_sample))
        idx = rng.choice(len(X_sample), size=n, replace=False)
        X_sub = X_sample[idx]
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sub)
        mean_abs = np.abs(shap_values).mean(axis=0)
        pairs = list(zip(feature_names, mean_abs.tolist()))
        pairs.sort(key=lambda x: x[1], reverse=True)
        return {k: round(v, 6) for k, v in pairs[:20]}
    except Exception as e:
        logger.warning("SHAP falhou (%s); usando gain importance.", e)
        return xgboost_gain_importance_top(model, feature_names)


def log_train_test_metrics(name: str, train_m: RegressionMetrics, test_m: RegressionMetrics) -> None:
    sep = "-" * 60
    logger.info(sep)
    logger.info("Avaliação — %s", name)
    logger.info(sep)
    logger.info("  Treino : %s", train_m)
    logger.info("  Teste  : %s", test_m)
    logger.info(sep)
    gap = train_m.r2 - test_m.r2
    if gap > 0.05:
        logger.warning("Gap R² treino-teste %.4f (>0.05): possível overfitting.", gap)
