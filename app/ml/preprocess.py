"""
Carregamento, limpeza e pipeline de pré-processamento.

Responsabilidades deste módulo:
- Ler os CSVs brutos de `data/raw/`
- Fazer o merge com dados demográficos por zipcode (quando disponível)
- Construir o ColumnTransformer do sklearn que será parte do pipeline salvo
- Expor constantes de features para uso em outros módulos

O preprocessor resultante é agnóstico ao modelo — pode ser reutilizado
com XGBoost, Ridge ou qualquer outro estimador.
"""

from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from app.core.config import settings
from app.core.logger import get_logger
from app.ml.feature_engineering import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    TARGET,
)

logger = get_logger(__name__)


# ── Carregamento ──────────────────────────────────────────────────────────────

def load_house_data(path: Path | None = None) -> pd.DataFrame:
    """
    Carrega o dataset KC House Sales e aplica limpezas básicas.

    Raises:
        FileNotFoundError: se o CSV não for encontrado no caminho informado.
    """
    csv_path = path or (settings.knowledge_base_path.parent / "raw" / "kc_house_data.csv")

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado em: {csv_path}\n"
            "Baixe o arquivo kc_house_data.csv do Kaggle e coloque em data/raw/."
        )

    logger.info(f"Carregando dataset de: {csv_path}")
    df = pd.read_csv(csv_path)
    logger.info(f"Dataset carregado: {df.shape[0]:,} linhas, {df.shape[1]} colunas")

    df = _clean_house_data(df)
    return df


def _clean_house_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica limpezas básicas:
    - Remove duplicatas por `id` (mantém a venda mais recente)
    - Corrige valores implausíveis (bedrooms == 0, preço == 0)
    - Garante tipos corretos
    """
    initial_len = len(df)

    # Mantém a venda mais recente para cada imóvel
    df = df.sort_values("date", ascending=False).drop_duplicates(subset="id")

    # Remove preços zerados ou negativos
    df = df[df[TARGET] > 0]

    # Corrige bedrooms outlier (33 bedrooms → provavelmente erro de digitação)
    df = df[df["bedrooms"] <= 20]

    # Garante tipos numéricos
    df["zipcode"] = df["zipcode"].astype(str)
    df["yr_renovated"] = df["yr_renovated"].fillna(0).astype(int)

    removed = initial_len - len(df)
    if removed > 0:
        logger.info(f"Limpeza: {removed} registros removidos")

    return df.reset_index(drop=True)


def load_demographics(path: Path | None = None) -> pd.DataFrame | None:
    """
    Carrega dados demográficos por zipcode se o arquivo existir.

    Retorna None se o arquivo não for encontrado (não obrigatório).
    """
    csv_path = path or (settings.knowledge_base_path.parent / "raw" / "zipcode_demographics.csv")

    if not csv_path.exists():
        logger.warning(
            "zipcode_demographics.csv não encontrado. "
            "Continuando sem dados demográficos."
        )
        return None

    logger.info(f"Carregando dados demográficos de: {csv_path}")
    df = pd.read_csv(csv_path, dtype={"zipcode": str})
    logger.info(f"Dados demográficos: {len(df)} zipcodes")
    return df


def merge_with_demographics(
    houses: pd.DataFrame,
    demographics: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Faz o merge entre imóveis e dados demográficos via zipcode.

    Usa left join para garantir que todos os imóveis sejam preservados,
    mesmo quando o zipcode não está na tabela de demografia.
    """
    if demographics is None:
        return houses

    merged = houses.merge(demographics, on="zipcode", how="left")
    logger.info(
        f"Merge concluído: {len(merged)} registros, "
        f"{merged.shape[1]} colunas"
    )
    return merged


# ── Pipeline de pré-processamento ─────────────────────────────────────────────

def build_preprocessor() -> ColumnTransformer:
    """
    Constrói o ColumnTransformer que será salvo como artefato.

    Decisão: não usamos StandardScaler para XGBoost (tree-based models
    são invariantes a escala). O scaler está disponível via `build_baseline_preprocessor`
    para o modelo linear de baseline.

    OrdinalEncoder no zipcode: eficiente para modelos de árvore — evita
    explosão de dimensionalidade do OneHotEncoder com ~70 zipcodes únicos.
    """
    numeric_transformer = SimpleImputer(strategy="median")

    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "encoder",
            OrdinalEncoder(
                handle_unknown="use_encoded_value",
                unknown_value=-1,
            ),
        ),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )

    return preprocessor


def build_baseline_preprocessor() -> ColumnTransformer:
    """
    Versão do preprocessor com StandardScaler para o modelo linear de baseline.
    """
    from sklearn.preprocessing import StandardScaler

    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "encoder",
            OrdinalEncoder(
                handle_unknown="use_encoded_value",
                unknown_value=-1,
            ),
        ),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )

    return preprocessor


def get_feature_names_out(preprocessor: ColumnTransformer) -> list[str]:
    """Retorna os nomes das features após transformação."""
    return NUMERIC_FEATURES + CATEGORICAL_FEATURES
