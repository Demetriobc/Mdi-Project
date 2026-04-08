"""
Serviço de explicação.

Orquestra o fluxo completo:
  Predição → RAG → Prompt → LLM → Explicação

É chamado pelo endpoint /chat quando o usuário pede explicação da previsão
e também internamente para gerar a explicação automática inicial.

Hierarquia respeitada:
  ML prevê → RAG contextualiza → LLM explica
"""

from __future__ import annotations

from app.api.schemas.chat import ChatMessage, ChatRequest, ChatResponse, PredictionContext
from app.api.services import llm_service, rag_service
from app.core.logger import get_logger
from app.rag.prompt_builder import SYSTEM_PROMPT

logger = get_logger(__name__)


def _format_prediction_block(ctx: PredictionContext) -> str:
    """Formata o bloco de contexto da predição para o prompt."""
    lines = [
        "=== RESULTADO DA PREDICAO ===",
        f"Preco previsto: {ctx.predicted_price_formatted}",
        f"Zipcode: {ctx.zipcode}",
        f"Area util: {ctx.sqft_living:,} sqft",
        f"Quartos: {ctx.bedrooms} | Banheiros: {ctx.bathrooms}",
        f"Qualidade de construcao (grade): {ctx.grade}/13",
        f"Condicao do imovel: {ctx.condition}/5",
    ]

    if ctx.zipcode_median_price:
        lines.append(f"Preco mediano do zipcode: US$ {ctx.zipcode_median_price:,.0f}")
    if ctx.price_vs_median_pct is not None:
        sign = "+" if ctx.price_vs_median_pct >= 0 else ""
        lines.append(
            f"Variacao vs. mediana do zipcode: {sign}{ctx.price_vs_median_pct:.1f}%"
        )
    if ctx.top_features:
        lines.append("\nTop features por importancia (SHAP):")
        for feat, val in list(ctx.top_features.items())[:5]:
            lines.append(f"  - {feat}: {val:.4f}")

    return "\n".join(lines)


def generate_initial_explanation(context: PredictionContext) -> ChatResponse:
    """
    Gera a explicação automática logo após uma predição.

    Chamada pela UI assim que o preço é exibido, sem interação do usuário.
    """
    logger.info(f"Gerando explicacao inicial para zipcode {context.zipcode}")

    chunks = rag_service.get_prediction_context_chunks(context)
    rag_ctx = rag_service.format_chunks_as_context(chunks)
    sources = rag_service.extract_sources(chunks)

    prediction_block = _format_prediction_block(context)

    system_content = (
        f"{SYSTEM_PROMPT}\n\n"
        f"{prediction_block}\n\n"
        f"{rag_ctx}"
    )

    task = (
        "Com base nas informacoes acima, escreva uma explicacao clara e objetiva "
        "sobre o preco previsto para este imovel. Inclua:\n"
        "1. Os principais fatores que justificam o preco (grade, localizacao, area, condicao)\n"
        "2. Como este imovel se posiciona em relacao ao mercado do zipcode\n"
        "3. Um breve comentario sobre o nivel de confianca desta previsao\n\n"
        "Use linguagem acessivel, seja direto e limite a resposta a 3 paragrafos."
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": task},
    ]

    answer, llm_ok = llm_service.call_llm(messages)

    return ChatResponse(answer=answer, sources=sources, llm_available=llm_ok)


def answer_chat_question(request: ChatRequest) -> ChatResponse:
    """
    Responde uma pergunta do usuário no chat contextual.

    Fluxo:
    1. Recupera chunks relevantes para a pergunta + contexto
    2. Monta prompt com histórico + contexto + RAG
    3. Chama LLM
    4. Retorna resposta com fontes
    """
    logger.info(f"Chat — pergunta: '{request.message[:60]}...'")

    chunks = rag_service.get_chat_context_chunks(
        request.message, request.prediction_context
    )
    rag_ctx = rag_service.format_chunks_as_context(chunks)
    sources = rag_service.extract_sources(chunks)

    # Monta system com todo o contexto disponível
    prediction_block = (
        _format_prediction_block(request.prediction_context)
        if request.prediction_context
        else "Nenhuma predicao ativa nesta sessao."
    )

    system_content = (
        f"{SYSTEM_PROMPT}\n\n"
        f"{prediction_block}\n\n"
        f"{rag_ctx}"
    )

    # Constrói a lista de mensagens respeitando o histórico
    MAX_HISTORY = 6
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_content}
    ]

    for turn in request.conversation_history[-MAX_HISTORY:]:
        messages.append({"role": turn.role, "content": turn.content})

    messages.append({"role": "user", "content": request.message})

    answer, llm_ok = llm_service.call_llm(messages)

    return ChatResponse(answer=answer, sources=sources, llm_available=llm_ok)
