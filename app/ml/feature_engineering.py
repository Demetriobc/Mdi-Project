"""
Engenharia de features para o dataset King County House Sales.

Implementa um transformer sklearn-compatível para que toda a lógica
de criação de features seja encapsulada no pipeline e aplicada de forma
idêntica em treino e inferência — sem risco de vazamento de dados.
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# O dataset KC cobre vendas de 2014-2015; usamos 2015 como referência
REFERENCE_YEAR: int = 2015

# Colunas removidas antes do pipeline (sem valor preditivo direto)
DROP_COLUMNS: list[str] = ["id", "date", "yr_built", "yr_renovated"]

# Features numéricas originais + engenheiradas que entram no preprocessor
NUMERIC_FEATURES: list[str] = [
    # originais
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
    # engenheiradas
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


class HousePriceFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Transformer que cria features derivadas do dataset KC House Sales.

    Pode ser inserido diretamente em um sklearn.pipeline.Pipeline porque
    implementa fit/transform com a interface padrão.

    Features criadas:
    - house_age: anos desde a construção
    - was_renovated: flag binária de renovação
    - years_since_renovation: anos desde a última renovação (ou construção)
    - living_lot_ratio: proporção entre área útil e lote
    - bath_bed_ratio: proporção quartos de banho / quartos
    - has_basement: flag binária de porão
    - living15_ratio: comparação da área útil com os 15 vizinhos mais próximos
    - sale_month: mês da venda extraído da coluna `date`
    """

    def fit(self, X: pd.DataFrame, y=None) -> "HousePriceFeatureEngineer":
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()

        # ── Features de idade ─────────────────────────────────────────────────
        df["house_age"] = REFERENCE_YEAR - df["yr_built"]
        df["was_renovated"] = (df["yr_renovated"] > 0).astype(int)
        df["years_since_renovation"] = np.where(
            df["yr_renovated"] > 0,
            REFERENCE_YEAR - df["yr_renovated"],
            df["house_age"],
        )

        # ── Ratios de tamanho ─────────────────────────────────────────────────
        df["living_lot_ratio"] = df["sqft_living"] / (df["sqft_lot"] + 1)
        df["bath_bed_ratio"] = df["bathrooms"] / (df["bedrooms"] + 1)
        df["has_basement"] = (df["sqft_basement"] > 0).astype(int)
        df["living15_ratio"] = df["sqft_living"] / (df["sqft_living15"] + 1)

        # ── Sazonalidade ──────────────────────────────────────────────────────
        if "date" in df.columns:
            df["sale_month"] = (
                pd.to_datetime(df["date"].astype(str).str[:8], format="%Y%m%d")
                .dt.month
            )
        else:
            df["sale_month"] = 1  # fallback para inferência sem coluna date

        return df
