"""System prompt + formatadores de texto (PredictionResult / RAG chunks)."""

from __future__ import annotations

from app.ml.predict import PredictionResult
from app.rag.retriever import RetrievedChunk


SYSTEM_PROMPT = """\
Você é o assistente do projeto madeinweb-teste, especializado em explicar previsões \
de preços de imóveis em King County, Washington (EUA).

Suas responsabilidades:
1. Explicar em linguagem clara POR QUE este imóvel (dados da sessão) foi \
avaliado no preço previsto pelo modelo de Machine Learning.
2. Responder à pergunta do usuário com foco no imóvel e no contexto fornecido.
3. Ser honesto sobre incertezas e limitações do modelo.

Regras importantes:
- O preço foi calculado por um modelo XGBoost. NÃO questione nem substitua \
esse valor — apenas explique com base no contexto.
- Use só o que está no contexto (predição + trechos RAG). Não invente números \
ou comparações de mercado não citadas.
- Responda em português do Brasil, tom profissional e acessível.

Brevidade (obrigatório):
- No chat: no máximo 2 parágrafos curtos OU até 6 linhas no total; prefira \
respostas diretas. Não escreva ensaios sobre “King County” ou regiões genéricas \
se a pergunta for sobre este imóvel — uma frase de contexto local basta.
- Na explicação automática após a predição: no máximo 2 parágrafos curtos \
(ou ~120 palavras).
- Evite repetir o preço previsto literalmente, salvo se a pergunta pedir o valor.
"""


def _format_prediction_context(result: PredictionResult) -> str:
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
    if not chunks:
        return "=== CONTEXTO DA BASE DE CONHECIMENTO ===\nNenhum contexto adicional disponível."

    lines = ["=== CONTEXTO DA BASE DE CONHECIMENTO ==="]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n[Fonte {i}: {chunk.source}]")
        lines.append(chunk.content.strip())

    return "\n".join(lines)


def build_explanation_prompt(
    result: PredictionResult,
    rag_chunks: list[RetrievedChunk],
) -> str:
    prediction_ctx = _format_prediction_context(result)
    rag_ctx = _format_rag_context(rag_chunks)

    return f"""\
{prediction_ctx}

{rag_ctx}

=== TAREFA ===
Em no máximo 2 parágrafos curtos (~120 palavras no total), explique o preço \
previsto para ESTE imóvel. Cubra em uma linha cada: (1) 2–3 fatores que mais \
pesam (use SHAP/top features quando existirem), (2) posição vs. mediana do \
zipcode se houver dado, (3) uma frase sobre limitação/confiança.

Sem introdução longa, sem lista de bairros genéricos fora do contexto fornecido.
"""


def build_chat_prompt(
    user_question: str,
    result: PredictionResult,
    rag_chunks: list[RetrievedChunk],
    conversation_history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
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
    return [
        {
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\n\n{prediction_context}\n\n{rag_context}",
        },
        {"role": "user", "content": user_question},
    ]
