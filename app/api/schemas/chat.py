"""
Schemas Pydantic para o endpoint de chat.

O contexto da predição é passado pelo cliente (Streamlit) em cada
requisição — mantendo a API stateless e sem necessidade de sessão.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Representa uma mensagem no histórico de conversa."""

    role: str = Field(description="'user' ou 'assistant'")
    content: str = Field(description="Conteúdo da mensagem")


class PredictionContext(BaseModel):
    """
    Resumo da predição ativa, enviado pelo cliente junto com cada pergunta.

    É uma versão compacta do PredictionResponse — contém apenas o que
    o LLM precisa para contextualizar a resposta.
    """

    predicted_price: float
    predicted_price_formatted: str
    zipcode: str
    sqft_living: int
    bedrooms: int
    bathrooms: float
    grade: int
    condition: int
    top_features: dict[str, float] = Field(default_factory=dict)
    zipcode_median_price: float | None = None
    price_vs_median_pct: float | None = None


class ChatRequest(BaseModel):
    """Requisição ao endpoint de chat."""

    message: str = Field(
        min_length=1,
        max_length=1000,
        description="Pergunta ou mensagem do usuário",
    )
    prediction_context: PredictionContext | None = Field(
        default=None,
        description="Contexto da predição ativa (opcional mas recomendado)",
    )
    conversation_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Histórico de turnos anteriores (máximo 10 turnos)",
    )

    model_config = {"json_schema_extra": {
        "example": {
            "message": "Por que essa casa ficou tão cara?",
            "prediction_context": {
                "predicted_price": 650000.0,
                "predicted_price_formatted": "US$ 650,000",
                "zipcode": "98103",
                "sqft_living": 2100,
                "bedrooms": 3,
                "bathrooms": 2.5,
                "grade": 9,
                "condition": 4,
                "top_features": {"sqft_living": 0.31, "grade": 0.19, "lat": 0.14},
                "zipcode_median_price": 645000.0,
                "price_vs_median_pct": 0.8,
            },
            "conversation_history": [],
        }
    }}


class ChatResponse(BaseModel):
    """Resposta do endpoint de chat."""

    answer: str = Field(description="Resposta gerada pelo LLM")
    sources: list[str] = Field(
        default_factory=list,
        description="Arquivos da knowledge base usados para contextualizar",
    )
    llm_available: bool = Field(
        default=True,
        description="False se o LLM não estava disponível e foi usada uma resposta de fallback",
    )
