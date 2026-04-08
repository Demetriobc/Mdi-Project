"""
Construção de prompts para o LLM.

Responsabilidade: montar o prompt final que será enviado ao LLM,
combinando o resultado da predição + trechos da knowledge base (RAG)
+ pergunta do usuário.

Princípio: o prompt deve sempre reforçar que o LLM é um explicador —
nunca deve tentar corrigir ou substituir a previsão do modelo de ML.
"""

from __future__ import annotations

from app.ml.predict import PredictionResult
from app.rag.retriever import RetrievedChunk


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Você é o House Price Copilot, um assistente especializado em explicar previsões \
de preços de imóveis em King County, Washington (EUA).

Suas responsabilidades:
1. Explicar em linguagem clara e acessível POR QUE um imóvel foi avaliado no \
preço previsto pelo modelo de Machine Learning.
2. Contextualizar a previsão com informações do mercado local (bairro, zipcode, \
tendências).
3. Responder perguntas sobre as features do imóvel, limitações do modelo e \
comparações de mercado.
4. Ser honesto sobre incertezas e limitações do modelo.

Regras importantes:
- O preço previsto foi calculado por um modelo XGBoost treinado em dados reais. \
NÃO questione nem substitua esse valor — sua função é explicá-lo.
- Use apenas as informações fornecidas no contexto. Não invente dados de mercado.
- Responda sempre em português do Brasil, de forma profissional mas acessível.
- Se não tiver informação suficiente para responder algo, diga claramente.
- Mantenha respostas concisas: 3–5 parágrafos no máximo para explicações, \
2–3 para perguntas diretas.
"""


# ── Formatadores de contexto ──────────────────────────────────────────────────

def _format_prediction_context(result: PredictionResult) -> str:
    """Formata o resultado da predição como bloco de contexto estruturado."""
    lines = [
        "=== RESULTADO DA PREDIÇÃO ===",
        f"Preço previsto: {result.predicted_price_formatted}",
        f"Zipcode: {result.zipcode}",
        f"Área útil: {result.sqft_living:,} sqft",
        f"Quartos: {result.bedrooms} | Banheiros: {result.bathrooms}",
        f"Qualidade de construção (grade): {result.grade}/13",
        f"Condição do imóvel: {result.condition}/5",
    ]

    if result.zipcode_median_price:
        lines.append(
            f"Preço mediano do zipcode: US$ {result.zipcode_median_price:,.0f}"
        )
    if result.price_vs_median_pct is not None:
        sign = "+" if result.price_vs_median_pct >= 0 else ""
        lines.append(
            f"Variação vs. mediana do zipcode: {sign}{result.price_vs_median_pct:.1f}%"
        )

    if result.top_features:
        lines.append("\nTop features por importância (SHAP):")
        for feat, importance in list(result.top_features.items())[:5]:
            lines.append(f"  - {feat}: {importance:.4f}")

    return "\n".join(lines)


def _format_rag_context(chunks: list[RetrievedChunk]) -> str:
    """Formata os trechos recuperados como bloco de contexto."""
    if not chunks:
        return "=== CONTEXTO DA BASE DE CONHECIMENTO ===\nNenhum contexto adicional disponível."

    lines = ["=== CONTEXTO DA BASE DE CONHECIMENTO ==="]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n[Fonte {i}: {chunk.source}]")
        lines.append(chunk.content.strip())

    return "\n".join(lines)


# ── Builders de prompt ────────────────────────────────────────────────────────

def build_explanation_prompt(
    result: PredictionResult,
    rag_chunks: list[RetrievedChunk],
) -> str:
    """
    Constrói o prompt para gerar a explicação automática da previsão.

    Chamado sempre que uma nova predição é feita, sem necessidade de
    interação do usuário.
    """
    prediction_ctx = _format_prediction_context(result)
    rag_ctx = _format_rag_context(rag_chunks)

    return f"""\
{prediction_ctx}

{rag_ctx}

=== TAREFA ===
Com base nas informações acima, escreva uma explicação clara e informativa sobre \
o preço previsto para este imóvel. Inclua:
1. Os principais fatores que justificam o preço (grade, localização, área, condição)
2. Como este imóvel se posiciona em relação ao mercado do zipcode
3. Um breve comentário sobre o nível de confiança desta previsão

Seja objetivo e use linguagem acessível para alguém que não é especialista em ML.
"""


def build_chat_prompt(
    user_question: str,
    result: PredictionResult,
    rag_chunks: list[RetrievedChunk],
    conversation_history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """
    Constrói a lista de mensagens para o chat contextual.

    Retorna no formato de messages da API OpenAI (system + user + assistant).

    Args:
        user_question: pergunta atual do usuário
        result: resultado da predição de contexto
        rag_chunks: trechos recuperados da KB
        conversation_history: histórico de turnos anteriores (opcional)
    """
    prediction_ctx = _format_prediction_context(result)
    rag_ctx = _format_rag_context(rag_chunks)

    system_with_context = f"""\
{SYSTEM_PROMPT}

Contexto atual da sessão:

{prediction_ctx}

{rag_ctx}
"""

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_with_context}
    ]

    # Histórico de conversa (mantém os últimos N turnos para não explodir o contexto)
    if conversation_history:
        MAX_HISTORY_TURNS = 6
        messages.extend(conversation_history[-MAX_HISTORY_TURNS:])

    messages.append({"role": "user", "content": user_question})

    return messages


def build_simple_chat_prompt(
    user_question: str,
    prediction_context: str,
    rag_context: str,
) -> list[dict[str, str]]:
    """
    Versão simplificada do builder para quando não há PredictionResult disponível,
    apenas strings de contexto pré-formatadas.
    """
    return [
        {
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\n\n{prediction_context}\n\n{rag_context}",
        },
        {"role": "user", "content": user_question},
    ]
