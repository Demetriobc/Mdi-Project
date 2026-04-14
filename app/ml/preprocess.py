"""
CSV → DataFrame limpo, merge opcional com demografia, ColumnTransformer (num + zipcode).

TargetEncoder no zipcode: média de preço suavizada no treino (evita one-hot gigante).
Ridge baseline usa StandardScaler nas numéricas; XGBoost não precisa de escala.
"""

from pathlib import Path

import pandas as pd
from category_encoders import TargetEncoder
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.core.config import settings
from app.core.logger import get_logger
from app.ml.feature_engineering import CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET

logger = get_logger(__name__)


def load_raw_kc_house_sales(path: Path | None = None) -> pd.DataFrame:
    csv_path = path or (settings.knowledge_base_path.parent / "raw" / "kc_house_data.csv")
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado: {csv_path}\n"
            "Coloque kc_house_data.csv em data/raw/ (Kaggle KC House Sales)."
        )
    logger.info("Carregando KC house sales de %s", csv_path)
    df = pd.read_csv(csv_path)
    logger.info("Linhas: %s, colunas: %s", f"{len(df):,}", df.shape[1])
    return clean_kc_house_sales(df)


def clean_kc_house_sales(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)
    df = df.sort_values("date", ascending=False).drop_duplicates(subset="id")
    df = df[df[TARGET] > 0]
    df = df[df["bedrooms"] <= 20]
    df["zipcode"] = df["zipcode"].astype(str)
    df["yr_renovated"] = df["yr_renovated"].fillna(0).astype(int)
    removed = n0 - len(df)
    if removed:
        logger.info("Limpeza removeu %s registros", removed)
    return df.reset_index(drop=True)


def load_zipcode_demographics_if_present(path: Path | None = None) -> pd.DataFrame | None:
    csv_path = path or (settings.knowledge_base_path.parent / "raw" / "zipcode_demographics.csv")
    if not csv_path.exists():
        logger.warning("zipcode_demographics.csv ausente; segue sem merge demográfico.")
        return None
    logger.info("Carregando demografia de %s", csv_path)
    demo = pd.read_csv(csv_path, dtype={"zipcode": str})
    logger.info("Zipcodes na demografia: %s", len(demo))
    return demo


def merge_housing_with_zipcode_demographics(
    houses: pd.DataFrame,
    demographics: pd.DataFrame | None,
) -> pd.DataFrame:
    if demographics is None:
        return houses
    merged = houses.merge(demographics, on="zipcode", how="left")
    logger.info("Merge demografia: %s linhas, %s colunas", len(merged), merged.shape[1])
    return merged


def make_xgboost_preprocessor() -> ColumnTransformer:
    numeric = SimpleImputer(strategy="median")
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                TargetEncoder(
                    smoothing=10.0,
                    min_samples_leaf=5,
                    handle_unknown="value",
                    handle_missing="value",
                ),
            ),
        ]
    )
    return ColumnTransformer(
        [("num", numeric, NUMERIC_FEATURES), ("cat", categorical, CATEGORICAL_FEATURES)],
        remainder="drop",
    )


def make_ridge_baseline_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                TargetEncoder(
                    smoothing=10.0,
                    min_samples_leaf=5,
                    handle_unknown="value",
                    handle_missing="value",
                ),
            ),
        ]
    )
    return ColumnTransformer(
        [("num", numeric, NUMERIC_FEATURES), ("cat", categorical, CATEGORICAL_FEATURES)],
        remainder="drop",
    )
