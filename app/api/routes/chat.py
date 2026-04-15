"""
Rota do chat contextual.

Endpoints:
  POST /chat            → responde pergunta com contexto ML + RAG + LLM
  POST /chat/explain    → gera explicação inicial para uma predição existente
"""

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.chat import ChatRequest, ChatResponse, PredictionContext
from app.api.services import explanation_service
from app.core.logger import get_logger

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Responde perguntas do usuário usando o contexto da predição + RAG + LLM.

    Exemplos de perguntas válidas:
    - "Por que essa casa ficou cara?"
    - "Quais variáveis influenciaram mais?"
    - "Essa previsão é confiável?"
    - "Como esse zipcode se compara aos outros?"
    - "Quais são as limitações desse modelo?"
    """
    try:
        return explanation_service.answer_chat_question(request)
    except Exception as e:
        logger.error(f"Erro no chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a pergunta.",
        ) from e


@router.post("/explain", response_model=ChatResponse)
async def explain(context: PredictionContext) -> ChatResponse:
    """
    Gera uma explicação automática para uma predição já realizada.

    Chamado pela UI automaticamente após exibir o preço previsto,
    sem necessidade de o usuário fazer uma pergunta explícita.
    """
    try:
        return explanation_service.generate_initial_explanation(context)
    except Exception as e:
        logger.error(f"Erro ao gerar explicacao: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar explicacao.",
        ) from e

