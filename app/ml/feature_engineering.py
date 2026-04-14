"""
Features derivadas do KC House Sales + transformer mínimo pro sklearn Pipeline.

O transformer só delega pra função pura: o fluxo fica explícito e o mesmo código
roda em treino e em inferência sem risco de divergir.
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# Dataset cobre 2014–2015; idade e sazonalidade usam 2015 como âncora (igual ao treino).
REFERENCE_YEAR: int = 2015

# Colunas que existem no CSV mas não entram no ColumnTransformer (remainder=drop).
DROP_COLUMNS: list[str] = ["id", "date", "yr_built", "yr_renovated"]

NUMERIC_FEATURES: list[str] = [
    "bedrooms",
    "bathrooms",
    "sqft_living",
    "sqft_lot",
    "floors",
    "waterfront",
    "view",
    "condition",
    "grade",
    "sqft_above",
    "sqft_basement",
    "sqft_living15",
    "sqft_lot15",
    "lat",
    "long",
    "house_age",
    "was_renovated",
    "years_since_renovation",
    "living_lot_ratio",
    "bath_bed_ratio",
    "has_basement",
    "living15_ratio",
    "sale_month",
]

CATEGORICAL_FEATURES: list[str] = ["zipcode"]

ALL_FEATURES: list[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

TARGET: str = "price"


def add_derived_housing_features(df: pd.DataFrame) -> pd.DataFrame:
    """Cria colunas derivadas; espera colunas do KC House (incl. date opcional na inferência)."""
    out = df.copy()

    out["house_age"] = REFERENCE_YEAR - out["yr_built"]
    out["was_renovated"] = (out["yr_renovated"] > 0).astype(int)
    out["years_since_renovation"] = np.where(
        out["yr_renovated"] > 0,
        REFERENCE_YEAR - out["yr_renovated"],
        out["house_age"],
    )

    out["living_lot_ratio"] = out["sqft_living"] / (out["sqft_lot"] + 1)
    out["bath_bed_ratio"] = out["bathrooms"] / (out["bedrooms"] + 1)
    out["has_basement"] = (out["sqft_basement"] > 0).astype(int)
    out["living15_ratio"] = out["sqft_living"] / (out["sqft_living15"] + 1)

    if "date" in out.columns:
        out["sale_month"] = (
            pd.to_datetime(out["date"].astype(str).str[:8], format="%Y%m%d").dt.month
        )
    else:
        # Inferência sem data de venda: mês neutro (mesmo fallback que o dataset costuma ter).
        out["sale_month"] = 1

    return out


class DerivedHousingFeatures(BaseEstimator, TransformerMixin):
    """Passo de Pipeline: só chama add_derived_housing_features."""

    def fit(self, X: pd.DataFrame, y=None) -> "DerivedHousingFeatures":
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return add_derived_housing_features(X)


# joblib dos modelos já treinados grava o path do pickle com este nome de classe.
HousePriceFeatureEngineer = DerivedHousingFeatures
