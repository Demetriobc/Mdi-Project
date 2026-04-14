"""
Schemas Pydantic para o endpoint de predição.

Separa claramente a fronteira entre o mundo externo (HTTP/JSON) e
o núcleo de ML. Toda validação de entrada acontece aqui — o modelo
nunca recebe dados sem passar por este schema.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Input ─────────────────────────────────────────────────────────────────────

class HouseInput(BaseModel):
    """
    Dados de entrada para predição de preço de um imóvel.

    Baseado no dataset King County House Sales (Seattle, WA).
    Todos os campos têm valores padrão para facilitar testes manuais.
    """

    bedrooms: Annotated[int, Field(ge=0, le=20, description="Número de quartos")] = 3
    bathrooms: Annotated[
        float, Field(ge=0.0, le=10.0, description="Número de banheiros (0.5 incrementos)")
    ] = 2.0
    sqft_living: Annotated[
        int, Field(ge=100, le=30_000, description="Área útil em sqft")
    ] = 1800
    sqft_lot: Annotated[
        int, Field(ge=100, le=2_000_000, description="Área total do lote em sqft")
    ] = 5000
    floors: Annotated[
        float, Field(ge=1.0, le=4.0, description="Número de andares (1.0, 1.5, 2.0, 2.5, 3.0)")
    ] = 1.0
    waterfront: Annotated[
        int, Field(ge=0, le=1, description="Vista para a água: 1=sim, 0=não")
    ] = 0
    view: Annotated[
        int, Field(ge=0, le=4, description="Qualidade da vista: 0 (nenhuma) a 4 (excelente)")
    ] = 0
    condition: Annotated[
        int, Field(ge=1, le=5, description="Condição geral: 1 (ruim) a 5 (excelente)")
    ] = 3
    grade: Annotated[
        int,
        Field(
            ge=1,
            le=13,
            description=(
                "Qualidade de construção e design (escala King County): "
                "1-3 abaixo do padrão, 7 médio, 11-13 luxo"
            ),
        ),
    ] = 7
    sqft_above: Annotated[
        int, Field(ge=100, le=20_000, description="Área acima do nível do solo em sqft")
    ] = 1800
    sqft_basement: Annotated[
        int, Field(ge=0, le=10_000, description="Área do porão em sqft (0 = sem porão)")
    ] = 0
    yr_built: Annotated[
        int, Field(ge=1900, le=2015, description="Ano de construção")
    ] = 1990
    yr_renovated: Annotated[
        int,
        Field(ge=0, le=2015, description="Ano de renovação (0 = nunca reformado)"),
    ] = 0
    zipcode: Annotated[
        str, Field(min_length=5, max_length=5, description="CEP de 5 dígitos (King County)")
    ] = "98103"
    lat: Annotated[
        float, Field(ge=47.0, le=48.0, description="Latitude (King County: ~47.1 a 47.8)")
    ] = 47.6
    long: Annotated[
        float, Field(ge=-123.0, le=-121.0, description="Longitude (King County: ~-122.5 a -121.3)")
    ] = -122.3
    sqft_living15: Annotated[
        int,
        Field(ge=100, le=20_000, description="Área útil média dos 15 vizinhos mais próximos em sqft"),
    ] = 1800
    sqft_lot15: Annotated[
        int,
        Field(ge=100, le=2_000_000, description="Área do lote média dos 15 vizinhos em sqft"),
    ] = 5000

    @field_validator("zipcode")
    @classmethod
    def zipcode_must_be_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("zipcode deve conter apenas dígitos")
        return v

    @model_validator(mode="after")
    def sqft_above_must_be_consistent(self) -> "HouseInput":
        """sqft_above não pode ser maior que sqft_living."""
        if self.sqft_above > self.sqft_living:
            raise ValueError(
                f"sqft_above ({self.sqft_above}) não pode ser maior que "
                f"sqft_living ({self.sqft_living})"
            )
        return self

    @model_validator(mode="after")
    def sqft_basement_must_be_consistent(self) -> "HouseInput":
        """sqft_basement deve ser consistente com sqft_living - sqft_above."""
        expected = self.sqft_living - self.sqft_above
        if self.sqft_basement > 0 and abs(self.sqft_basement - expected) > 200:
            # Aviso suave — não bloqueia, apenas sinaliza inconsistência
            pass
        return self

    def to_model_input(self) -> dict[str, Any]:
        """
        Converte o schema para o dicionário esperado pelo pipeline de ML.

        Sem `date`: na inferência `sale_month` cai no fallback (=1), igual ao pipeline.
        """
        return self.model_dump()


# ── Output ────────────────────────────────────────────────────────────────────

class PredictionResponse(BaseModel):
    """Resposta completa da predição retornada pela API."""

    predicted_price: float = Field(description="Preço previsto em USD")
    predicted_price_formatted: str = Field(description="Preço formatado (ex: US$ 450,000)")

    # Dados do imóvel refletidos
    zipcode: str
    sqft_living: int
    bedrooms: int
    bathrooms: float
    grade: int
    condition: int

    # Contexto de mercado (pode ser null quando não disponível)
    zipcode_median_price: float | None = Field(
        default=None,
        description="Mediana de preço do zipcode (calculada do dataset de treino)",
    )
    price_vs_median_pct: float | None = Field(
        default=None,
        description="Quanto o preço previsto desvia da mediana do zipcode (%)",
    )

    # Intervalo de confiança (P10–P90 via quantile regression)
    # ~80% de probabilidade de o preço real ficar dentro deste intervalo
    price_p10: float | None = Field(
        default=None,
        description="Limite inferior do intervalo de confiança (percentil 10)",
    )
    price_p90: float | None = Field(
        default=None,
        description="Limite superior do intervalo de confiança (percentil 90)",
    )

    # Metadados do modelo
    model_version: str = Field(description="Data de treino do modelo (YYYY-MM-DD)")
    top_features: dict[str, float] = Field(
        default_factory=dict,
        description="Top features por importância (SHAP ou feature_importances_)",
    )

    model_config = {"protected_namespaces": (), "json_schema_extra": {
        "example": {
            "predicted_price": 452000.0,
            "predicted_price_formatted": "US$ 452,000",
            "zipcode": "98103",
            "sqft_living": 1800,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "grade": 8,
            "condition": 3,
            "zipcode_median_price": 430000.0,
            "price_vs_median_pct": 5.1,
            "model_version": "2024-01-15",
            "top_features": {
                "sqft_living": 0.312,
                "grade": 0.187,
                "lat": 0.143,
                "zipcode": 0.098,
                "sqft_above": 0.071,
            },
        }
    }}


class BatchPredictionRequest(BaseModel):
    """Requisição de predição em lote."""

    houses: list[HouseInput] = Field(
        min_length=1,
        max_length=100,
        description="Lista de imóveis para predição (máximo 100 por chamada)",
    )


class BatchPredictionResponse(BaseModel):
    """Resposta de predição em lote."""

    predictions: list[PredictionResponse]
    count: int
    model_version: str
