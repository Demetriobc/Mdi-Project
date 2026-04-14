"""
Treino: CSV → split temporal → Ridge baseline → XGBoost (p50 + p10/p90) → métricas → joblib/json.

    python -m app.ml.train
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

from app.core.logger import get_logger
from app.ml.evaluate import (
    dollar_space_regression_metrics,
    log_train_test_metrics,
    mean_abs_shap_importance_top,
    xgboost_gain_importance_top,
)
from app.ml.feature_engineering import ALL_FEATURES, DerivedHousingFeatures, TARGET
from app.ml.model_registry import save_house_price_artifacts
from app.ml.preprocess import (
    load_raw_kc_house_sales,
    load_zipcode_demographics_if_present,
    make_ridge_baseline_preprocessor,
    make_xgboost_preprocessor,
    merge_housing_with_zipcode_demographics,
)

logger = get_logger(__name__)

XGB_PARAMS: dict = {
    "n_estimators": 600,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "reg_alpha": 0.1,
    "reg_lambda": 1.5,
    "tree_method": "hist",
    "random_state": 42,
    "verbosity": 0,
    "n_jobs": -1,
}

RIDGE_ALPHA = 10.0
RANDOM_STATE = 42
SPLIT_DATE = "20150101"


def split_train_test_by_sale_date(
    raw_data_path: Path | None = None,
    demographics_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Treino = vendas antes de SPLIT_DATE; teste = a partir (simula prever o futuro).
    y em dólares; X sem coluna price.
    """
    houses = load_raw_kc_house_sales(raw_data_path)
    demographics = load_zipcode_demographics_if_present(demographics_path)
    df = merge_housing_with_zipcode_demographics(houses, demographics)

    y = df[TARGET]
    X = df.drop(columns=[TARGET])

    dates = pd.to_datetime(X["date"].astype(str).str[:8], format="%Y%m%d")
    cutoff = pd.Timestamp(SPLIT_DATE)
    train_mask = dates < cutoff

    X_train = X[train_mask].copy()
    X_test = X[~train_mask].copy()
    y_train = y[train_mask]
    y_test = y[~train_mask]

    logger.info(
        "Split %s — treino %s / teste %s",
        SPLIT_DATE,
        f"{train_mask.sum():,}",
        f"{(~train_mask).sum():,}",
    )
    logger.info(
        "Preço médio treino $%s | teste $%s",
        f"{y_train.mean():,.0f}",
        f"{y_test.mean():,.0f}",
    )
    return X_train, X_test, y_train, y_test


def train_ridge_baseline(X_train: pd.DataFrame, y_train: pd.Series) -> Pipeline:
    pipeline = Pipeline(
        [
            ("features", DerivedHousingFeatures()),
            ("prep", make_ridge_baseline_preprocessor()),
            ("model", Ridge(alpha=RIDGE_ALPHA)),
        ]
    )
    y_log = np.log1p(y_train.values)
    pipeline.fit(X_train, y_log)
    logger.info("Ridge baseline ok.")
    return pipeline


def optimal_n_estimators_from_validation_holdout(
    X_train: pd.DataFrame,
    y_train_log: np.ndarray,
    early_stopping_rounds: int = 50,
    val_size: float = 0.1,
) -> int:
    """10% de X_train como validação; early stopping no RMSE (log)."""
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_train, y_train_log, test_size=val_size, random_state=RANDOM_STATE
    )
    prep = Pipeline(
        [
            ("features", DerivedHousingFeatures()),
            ("prep", make_xgboost_preprocessor()),
        ]
    )
    X_tr_p = prep.fit_transform(X_tr, y_tr)
    X_val_p = prep.transform(X_val)

    xgb_es = XGBRegressor(
        **XGB_PARAMS,
        early_stopping_rounds=early_stopping_rounds,
        eval_metric="rmse",
    )
    xgb_es.fit(X_tr_p, y_tr, eval_set=[(X_val_p, y_val)], verbose=False)
    best_n = xgb_es.best_iteration + 1
    logger.info("Early stopping: n_estimators=%s (cap %s)", best_n, XGB_PARAMS["n_estimators"])
    return best_n


def train_xgboost_median_and_quantiles(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> tuple[Pipeline, Pipeline, Pipeline, Pipeline]:
    y_log = np.log1p(y_train.values)
    n_est = optimal_n_estimators_from_validation_holdout(X_train, y_log)
    params = {**XGB_PARAMS, "n_estimators": n_est}

    full = Pipeline(
        [
            ("features", DerivedHousingFeatures()),
            ("prep", make_xgboost_preprocessor()),
            ("model", XGBRegressor(**params)),
        ]
    )
    full.fit(X_train, y_log)
    logger.info("XGBoost p50 treinado (n_estimators=%s).", n_est)

    prep_only = Pipeline(
        [
            ("features", DerivedHousingFeatures()),
            ("prep", make_xgboost_preprocessor()),
        ]
    )
    prep_only.fit(X_train, y_log)

    qbase = {**params, "objective": "reg:quantileerror"}
    p10 = Pipeline(
        [
            ("features", DerivedHousingFeatures()),
            ("prep", make_xgboost_preprocessor()),
            ("model", XGBRegressor(**{**qbase, "quantile_alpha": 0.1})),
        ]
    )
    p10.fit(X_train, y_log)
    p90 = Pipeline(
        [
            ("features", DerivedHousingFeatures()),
            ("prep", make_xgboost_preprocessor()),
            ("model", XGBRegressor(**{**qbase, "quantile_alpha": 0.9})),
        ]
    )
    p90.fit(X_train, y_log)
    logger.info("Quantis p10/p90 ok.")

    return full, prep_only, p10, p90


def train_and_save_house_price_xgboost(
    raw_data_path: Path | None = None,
    demographics_path: Path | None = None,
) -> None:
    logger.info("=== Treino house price ===")

    X_train, X_test, y_train, y_test = split_train_test_by_sale_date(
        raw_data_path, demographics_path
    )
    y_train_log = np.log1p(y_train.values)
    y_test_log = np.log1p(y_test.values)

    logger.info("Ridge baseline...")
    baseline = train_ridge_baseline(X_train, y_train)
    b_tr = dollar_space_regression_metrics(y_train_log, baseline.predict(X_train))
    b_te = dollar_space_regression_metrics(y_test_log, baseline.predict(X_test))
    log_train_test_metrics("Ridge baseline", b_tr, b_te)

    logger.info("XGBoost p50 + p10/p90...")
    xgb_full, prep_only, pipe_p10, pipe_p90 = train_xgboost_median_and_quantiles(X_train, y_train)
    x_tr = dollar_space_regression_metrics(y_train_log, xgb_full.predict(X_train))
    x_te = dollar_space_regression_metrics(y_test_log, xgb_full.predict(X_test))
    log_train_test_metrics("XGBoost p50", x_tr, x_te)

    p10_usd = np.expm1(pipe_p10.predict(X_test))
    p90_usd = np.expm1(pipe_p90.predict(X_test))
    y_te_usd = y_test.values
    coverage = float(np.mean((y_te_usd >= p10_usd) & (y_te_usd <= p90_usd)))
    avg_width = float(np.mean(p90_usd - p10_usd))
    logger.info(
        "P10–P90 no teste: cobertura %.1f%% | largura média $%s",
        coverage * 100,
        f"{avg_width:,.0f}",
    )

    logger.info(
        "XGB vs Ridge (teste): R² +%.4f | MAE %.1f%% menor",
        x_te.r2 - b_te.r2,
        (b_te.mae - x_te.mae) / b_te.mae * 100,
    )
    logger.info("Gap R² treino-teste (XGB): %.4f", x_tr.r2 - x_te.r2)

    xgb_model = xgb_full.named_steps["model"]
    feature_names = list(ALL_FEATURES)
    X_test_matrix = prep_only.transform(X_test)
    shap_imp = mean_abs_shap_importance_top(xgb_model, X_test_matrix, feature_names)

    zip_median = (
        X_train.assign(price=y_train.values)
        .groupby("zipcode")["price"]
        .median()
        .round(2)
        .to_dict()
    )

    metadata = {
        "model_type": "XGBRegressor",
        "model_params": {**XGB_PARAMS, "n_estimators": xgb_model.n_estimators},
        "target": "price",
        "target_transform": "log1p",
        "features": feature_names,
        "n_features": len(feature_names),
        "trained_at": datetime.now(tz=timezone.utc).isoformat(),
        "split": {"type": "temporal", "cutoff_date": SPLIT_DATE},
        "data_info": {
            "n_train": len(X_train),
            "n_test": len(X_test),
            "price_stats": {
                "train_mean": round(float(y_train.mean()), 2),
                "train_median": round(float(y_train.median()), 2),
                "train_std": round(float(y_train.std()), 2),
                "test_mean": round(float(y_test.mean()), 2),
                "test_median": round(float(y_test.median()), 2),
            },
        },
        "metrics": {
            "baseline": {"train": b_tr.to_dict(), "test": b_te.to_dict()},
            "xgboost": {"train": x_tr.to_dict(), "test": x_te.to_dict()},
        },
        "confidence_intervals": {
            "coverage_p10_p90": round(coverage, 4),
            "avg_interval_usd": round(avg_width, 2),
        },
        "feature_importance": xgboost_gain_importance_top(xgb_model, feature_names),
        "shap_importance": shap_imp,
        "zipcode_median_prices": zip_median,
    }

    save_house_price_artifacts(
        model=xgb_full,
        preprocessor=prep_only,
        metadata=metadata,
        model_p10=pipe_p10,
        model_p90=pipe_p90,
    )
    logger.info("Artefatos em artifacts/model/")


if __name__ == "__main__":
    train_and_save_house_price_xgboost()
