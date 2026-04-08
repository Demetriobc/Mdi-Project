"""
Pipeline de treinamento end-to-end.

Fluxo:
1. Carrega dados brutos de `data/raw/`
2. Aplica feature engineering
3. Separa treino / teste (80/20, estratificado por faixa de preço)
4. Treina modelo baseline (Ridge)
5. Treina modelo final (XGBoost)
6. Avalia ambos com métricas de regressão
7. Salva artefatos em `artifacts/model/`

Como executar:
    python -m app.ml.train
    make train
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
    compute_feature_importance,
    compute_metrics,
    compute_shap_importance,
    log_evaluation_report,
)
from app.ml.feature_engineering import (
    ALL_FEATURES,
    DROP_COLUMNS,
    HousePriceFeatureEngineer,
    TARGET,
)
from app.ml.model_registry import save_all
from app.ml.preprocess import (
    build_baseline_preprocessor,
    build_preprocessor,
    get_feature_names_out,
    load_demographics,
    load_house_data,
    merge_with_demographics,
)

logger = get_logger(__name__)

# ── Hiperparâmetros ───────────────────────────────────────────────────────────
# Configuração balanceada para o dataset KC (~21k registros).
# n_estimators alto com learning_rate baixo → convergência estável.
# early_stopping não é usado aqui para manter o pipeline simples e
# reprodutível sem conjunto de validação separado.
XGB_PARAMS: dict = {
    "n_estimators": 600,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "tree_method": "hist",   # Mais rápido para CPU
    "random_state": 42,
    "verbosity": 0,
    "n_jobs": -1,
}

RIDGE_ALPHA: float = 10.0
TEST_SIZE: float = 0.2
RANDOM_STATE: int = 42


# ── Funções auxiliares ────────────────────────────────────────────────────────

def _log_transform_target(y: pd.Series) -> np.ndarray:
    """
    Aplica log1p na variável alvo.

    Razão: distribuição de preços é assimétrica à direita (long tail).
    Log transform aproxima de uma normal e melhora o desempenho de
    modelos lineares e gradiente boosting.
    """
    return np.log1p(y.values)


def _price_bin(price: float) -> int:
    """Categoriza preço em faixas para estratificação do split."""
    if price < 300_000:
        return 0
    elif price < 600_000:
        return 1
    elif price < 1_000_000:
        return 2
    else:
        return 3


def prepare_data(
    raw_data_path: Path | None = None,
    demographics_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """
    Carrega, limpa, faz merge e divide os dados em treino/teste.

    Returns:
        X_train, X_test, y_train, y_test
    """
    houses = load_house_data(raw_data_path)
    demographics = load_demographics(demographics_path)
    df = merge_with_demographics(houses, demographics)

    # Separar target antes do feature engineering
    y = df[TARGET]
    X = df.drop(columns=[TARGET])

    # Estratificação por faixa de preço para distribuição balanceada
    price_bins = y.apply(_price_bin)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=price_bins,
    )

    logger.info(
        f"Split: {len(X_train):,} treino / {len(X_test):,} teste "
        f"({TEST_SIZE:.0%} teste)"
    )
    logger.info(
        f"Preço médio — treino: ${y_train.mean():,.0f} | "
        f"teste: ${y_test.mean():,.0f}"
    )

    return X_train, X_test, y_train, y_test


# ── Treino baseline ───────────────────────────────────────────────────────────

def train_baseline(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
) -> Pipeline:
    """
    Treina um Ridge Regression como baseline.

    Serve como referência mínima de performance. Se o XGBoost não superar
    o baseline significativamente, há algo errado com os dados ou o pipeline.
    """
    feature_engineer = HousePriceFeatureEngineer()
    preprocessor = build_baseline_preprocessor()

    pipeline = Pipeline([
        ("feature_engineer", feature_engineer),
        ("preprocessor", preprocessor),
        ("model", Ridge(alpha=RIDGE_ALPHA)),
    ])

    y_log = _log_transform_target(y_train)
    pipeline.fit(X_train, y_log)

    logger.info("Baseline (Ridge) treinado.")
    return pipeline


# ── Treino modelo final ───────────────────────────────────────────────────────

def train_xgboost(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
) -> tuple[Pipeline, Pipeline]:
    """
    Treina o modelo XGBoost final.

    Returns:
        full_pipeline: Pipeline completo (feature_eng + preprocessor + xgb)
        preprocessor_pipeline: Pipeline sem o modelo (para salvar separado)
    """
    feature_engineer = HousePriceFeatureEngineer()
    preprocessor = build_preprocessor()

    xgb = XGBRegressor(**XGB_PARAMS)

    full_pipeline = Pipeline([
        ("feature_engineer", feature_engineer),
        ("preprocessor", preprocessor),
        ("model", xgb),
    ])

    y_log = _log_transform_target(y_train)
    full_pipeline.fit(X_train, y_log)

    logger.info(
        f"XGBoost treinado. "
        f"n_estimators: {XGB_PARAMS['n_estimators']}, "
        f"max_depth: {XGB_PARAMS['max_depth']}"
    )

    # Pipeline de pré-processamento separado (para salvar como artefato)
    preprocessor_pipeline = Pipeline([
        ("feature_engineer", HousePriceFeatureEngineer()),
        ("preprocessor", build_preprocessor()),
    ])
    preprocessor_pipeline.fit(X_train)

    return full_pipeline, preprocessor_pipeline


# ── Ponto de entrada ──────────────────────────────────────────────────────────

def run_training(
    raw_data_path: Path | None = None,
    demographics_path: Path | None = None,
) -> None:
    """
    Executa o pipeline de treinamento completo.

    Ordem:
    1. Prepara dados (load → clean → merge → split)
    2. Treina baseline
    3. Treina XGBoost
    4. Avalia ambos
    5. Salva artefatos do XGBoost (modelo, preprocessor, metadata)
    """
    logger.info("=" * 60)
    logger.info("Iniciando pipeline de treinamento")
    logger.info("=" * 60)

    # 1. Dados
    X_train, X_test, y_train, y_test = prepare_data(raw_data_path, demographics_path)
    y_train_log = np.log1p(y_train.values)
    y_test_log = np.log1p(y_test.values)

    # 2. Baseline
    logger.info("\n[1/2] Treinando baseline (Ridge)...")
    baseline = train_baseline(X_train, y_train)
    baseline_pred_train = baseline.predict(X_train)
    baseline_pred_test = baseline.predict(X_test)

    baseline_train_metrics = compute_metrics(y_train_log, baseline_pred_train)
    baseline_test_metrics = compute_metrics(y_test_log, baseline_pred_test)
    log_evaluation_report("Ridge Baseline", baseline_train_metrics, baseline_test_metrics)

    # 3. XGBoost
    logger.info("\n[2/2] Treinando XGBoost...")
    xgb_pipeline, preprocessor_pipeline = train_xgboost(X_train, y_train)
    xgb_pred_train = xgb_pipeline.predict(X_train)
    xgb_pred_test = xgb_pipeline.predict(X_test)

    xgb_train_metrics = compute_metrics(y_train_log, xgb_pred_train)
    xgb_test_metrics = compute_metrics(y_test_log, xgb_pred_test)
    log_evaluation_report("XGBoost Final", xgb_train_metrics, xgb_test_metrics)

    # 4. Comparativo
    improvement_r2 = xgb_test_metrics.r2 - baseline_test_metrics.r2
    improvement_mae = (
        (baseline_test_metrics.mae - xgb_test_metrics.mae)
        / baseline_test_metrics.mae * 100
    )
    logger.info(
        f"\nXGBoost vs Baseline: "
        f"R² +{improvement_r2:.4f} | "
        f"MAE -{improvement_mae:.1f}%"
    )

    # 5. Metadados e save
    xgb_model = xgb_pipeline.named_steps["model"]
    feature_names = get_feature_names_out(
        preprocessor_pipeline.named_steps["preprocessor"]
    )

    # Calcula feature importance com SHAP (amostra do teste)
    X_test_processed = preprocessor_pipeline.transform(X_test)
    shap_importance = compute_shap_importance(xgb_model, X_test_processed, feature_names)

    # Medianas de preço por zipcode do conjunto de treino — usadas pelo
    # prediction_service para enriquecer respostas com contexto de mercado.
    # Calculadas APENAS no treino para evitar vazamento de dados.
    zipcode_median_prices = (
        X_train.assign(price=y_train.values)
        .groupby("zipcode")["price"]
        .median()
        .round(2)
        .to_dict()
    )
    logger.info(f"Medianas de preço calculadas para {len(zipcode_median_prices)} zipcodes")

    metadata = {
        "model_type": "XGBRegressor",
        "model_params": XGB_PARAMS,
        "target": "price",
        "target_transform": "log1p",
        "features": feature_names,
        "n_features": len(feature_names),
        "trained_at": datetime.now(tz=timezone.utc).isoformat(),
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
            "baseline": {
                "train": baseline_train_metrics.to_dict(),
                "test": baseline_test_metrics.to_dict(),
            },
            "xgboost": {
                "train": xgb_train_metrics.to_dict(),
                "test": xgb_test_metrics.to_dict(),
            },
        },
        "feature_importance": compute_feature_importance(xgb_model, feature_names),
        "shap_importance": shap_importance,
        "zipcode_median_prices": zipcode_median_prices,
    }

    save_all(
        model=xgb_pipeline,
        preprocessor=preprocessor_pipeline,
        metadata=metadata,
    )

    logger.info("\nTreinamento concluido. Artefatos salvos em artifacts/model/")


if __name__ == "__main__":
    run_training()
