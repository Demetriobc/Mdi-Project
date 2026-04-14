"""OpenAI-compatible client (OpenAI ou Groq); devolve texto + flag de sucesso."""

from __future__ import annotations

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Mensagem exibida quando o LLM não está disponível
LLM_UNAVAILABLE_MESSAGE = (
    "O assistente de IA não está disponível no momento "
    "(provedor LLM não configurado ou sem créditos). "
    "A previsão de preço acima foi gerada pelo modelo de Machine Learning "
    "e permanece válida."
)


def call_llm(
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> tuple[str, bool]:
    """Retorna (texto, ok). Se falhar ou sem chave, texto é mensagem amigável e ok=False."""
    if not settings.has_llm_key:
        logger.warning("LLM nao chamado: chave do provedor nao configurada.")
        return LLM_UNAVAILABLE_MESSAGE, False

    try:
        from openai import OpenAI

        provider = settings.llm_provider.lower()
        model = settings.openai_model
        api_key = settings.openai_api_key
        temperature_default = settings.openai_temperature
        max_tokens_default = settings.openai_max_tokens
        client_kwargs: dict[str, str] = {"api_key": api_key}

        if provider == "groq":
            model = settings.groq_model
            api_key = settings.groq_api_key
            temperature_default = settings.groq_temperature
            max_tokens_default = settings.groq_max_tokens
            client_kwargs = {
                "api_key": api_key,
                "base_url": "https://api.groq.com/openai/v1",
            }

        client = OpenAI(**client_kwargs)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature if temperature is not None else temperature_default,
            max_tokens=max_tokens if max_tokens is not None else max_tokens_default,
        )

        answer = response.choices[0].message.content or ""
        logger.debug(
            f"LLM ({provider}) respondeu: {len(answer)} chars | "
            f"tokens usados: {response.usage.total_tokens if response.usage else 'N/A'}"
        )
        return answer.strip(), True

    except Exception as e:
        logger.error(f"Erro ao chamar LLM: {type(e).__name__}: {e}")
        return _fallback_message(e), False


def _fallback_message(error: Exception) -> str:
    error_str = str(error).lower()

    if "quota" in error_str or "insufficient" in error_str or "429" in error_str:
        return (
            "Limite de cota do provedor de IA atingido. "
            "A previsao de preco do modelo de ML permanece valida. "
            "Adicione creditos no provedor configurado para habilitar as explicacoes em linguagem natural."
        )
    if "api_key" in error_str or "authentication" in error_str or "401" in error_str:
        return (
            "Chave do provedor de IA invalida ou nao configurada. "
            "Configure OPENAI_API_KEY ou GROQ_API_KEY no arquivo .env para habilitar o chat."
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
