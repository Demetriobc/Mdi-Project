"""
Serviço de LLM.

Responsabilidade única: enviar mensagens formatadas à API da OpenAI e
retornar a resposta. Não sabe nada sobre predição, RAG ou contexto de negócio.

Inclui fallback gracioso para quando o LLM não está disponível
(sem API key, sem créditos, timeout), garantindo que o resto do sistema
continue funcionando.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Mensagem exibida quando o LLM não está disponível
LLM_UNAVAILABLE_MESSAGE = (
    "O assistente de IA não está disponível no momento "
    "(chave OpenAI não configurada ou sem créditos). "
    "A previsão de preço acima foi gerada pelo modelo de Machine Learning "
    "e permanece válida."
)


def call_llm(
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> tuple[str, bool]:
    """
    Chama o LLM com a lista de mensagens fornecida.

    Args:
        messages: lista no formato OpenAI [{"role": ..., "content": ...}]
        temperature: sobrescreve o padrão do settings se fornecido
        max_tokens: sobrescreve o padrão do settings se fornecido

    Returns:
        (resposta_texto, llm_disponivel)
        Se o LLM falhar, retorna (mensagem_fallback, False).
    """
    if not settings.has_openai_key:
        logger.warning("LLM não chamado: OPENAI_API_KEY não configurada.")
        return LLM_UNAVAILABLE_MESSAGE, False

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)

        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=temperature or settings.openai_temperature,
            max_tokens=max_tokens or settings.openai_max_tokens,
        )

        answer = response.choices[0].message.content or ""
        logger.debug(
            f"LLM respondeu: {len(answer)} chars | "
            f"tokens usados: {response.usage.total_tokens if response.usage else 'N/A'}"
        )
        return answer.strip(), True

    except Exception as e:
        logger.error(f"Erro ao chamar LLM: {type(e).__name__}: {e}")
        return _fallback_message(e), False


def _fallback_message(error: Exception) -> str:
    """Gera mensagem de fallback baseada no tipo de erro."""
    error_str = str(error).lower()

    if "quota" in error_str or "insufficient" in error_str or "429" in error_str:
        return (
            "Limite de cota da OpenAI atingido. "
            "A previsao de preco do modelo de ML permanece valida. "
            "Adicione creditos em platform.openai.com para habilitar as explicacoes em linguagem natural."
        )
    if "api_key" in error_str or "authentication" in error_str or "401" in error_str:
        return (
            "Chave da OpenAI invalida ou nao configurada. "
            "Configure OPENAI_API_KEY no arquivo .env para habilitar o chat."
        )
    if "timeout" in error_str:
        return (
            "Timeout ao conectar ao servico de IA. "
            "Tente novamente em alguns instantes."
        )

    return (
        "Servico de IA temporariamente indisponivel. "
        "A previsao de preco continua valida."
    )
