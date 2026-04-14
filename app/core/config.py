"""
Configuração central da aplicação.

Usa pydantic-settings para carregar variáveis de ambiente com validação de tipos
e valores padrão. Um único objeto `settings` é instanciado e reutilizado em
todo o projeto — sem chamar os.getenv() espalhado pelo código.

Ambientes suportados (controlado por APP_ENV):
  - development (padrão): logs verbose, validações relaxadas
  - staging:              como produção, mas sem exigir DATABASE_URL
  - production:           validações estritas, JSON logging
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # ── Aplicação ─────────────────────────────────────────────────────────────
    app_env: str = Field(default="development")
    app_name: str = Field(default="madeinweb-teste")
    app_version: str = Field(default="0.1.0")
    log_level: str = Field(default="INFO")

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    # Railway (e outros PaaS) injetam PORT; localmente use API_PORT ou omita.
    api_port: int = Field(
        default=8001,
        validation_alias=AliasChoices("PORT", "API_PORT"),
    )

    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_provider: str = Field(default="openai")  # "openai" | "groq"
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    openai_temperature: float = Field(default=0.3)
    openai_max_tokens: int = Field(default=1024)
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.1-8b-instant")
    groq_temperature: float = Field(default=0.3)
    groq_max_tokens: int = Field(default=1024)

    # ── RAG ───────────────────────────────────────────────────────────────────
    embedding_provider: str = Field(default="local")  # "local" | "openai"
    vectorstore_path: Path = Field(default=Path("artifacts/vectorstore"))
    knowledge_base_path: Path = Field(default=Path("data/knowledge_base"))
    rag_top_k: int = Field(default=4)

    # ── Artefatos ML ──────────────────────────────────────────────────────────
    model_path: Path = Field(default=Path("artifacts/model/house_price_model.joblib"))
    model_p10_path: Path = Field(default=Path("artifacts/model/house_price_model_p10.joblib"))
    model_p90_path: Path = Field(default=Path("artifacts/model/house_price_model_p90.joblib"))
    preprocessor_path: Path = Field(default=Path("artifacts/model/preprocessor.joblib"))
    metadata_path: Path = Field(default=Path("artifacts/model/metadata.json"))

    # ── Banco de dados ────────────────────────────────────────────────────────
    database_url: str = Field(default="")

    # ── UI / CORS ───────────────────────────────────────────────────────────────
    api_base_url: str = Field(default="http://localhost:8001")
    # Produção: origens do browser que podem chamar a API (separadas por vírgula).
    # Ex.: https://meu-app.vercel.app,http://localhost:5173
    cors_origins: str = Field(default="")

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def has_openai_key(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key not in ("", "sk-..."))

    @property
    def has_groq_key(self) -> bool:
        return bool(self.groq_api_key and self.groq_api_key not in ("", "gsk-..."))

    @property
    def has_llm_key(self) -> bool:
        provider = self.llm_provider.lower()
        if provider == "groq":
            return self.has_groq_key
        return self.has_openai_key

    # ── Validação de dependências cruzadas ────────────────────────────────────

    @model_validator(mode="after")
    def validate_cross_dependencies(self) -> Self:
        """
        Verifica dependências cruzadas entre configurações.
        Falha no startup com mensagem clara em vez de erro opaco em runtime.
        """
        errors: list[str] = []

        provider = self.llm_provider.lower()

        if provider not in ("openai", "groq"):
            errors.append("LLM_PROVIDER deve ser 'openai' ou 'groq'")

        if self.embedding_provider == "openai" and not self.has_openai_key:
            errors.append(
                "EMBEDDING_PROVIDER=openai exige OPENAI_API_KEY configurada"
            )

        if errors:
            raise ValueError(
                "Configuração inválida:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        return self


class DevSettings(Settings):
    """Configurações para ambiente de desenvolvimento — logs verbose, validações relaxadas."""

    app_env: str = Field(default="development")
    log_level: str = Field(default="DEBUG")


class StagingSettings(Settings):
    """Configurações para staging — espelha produção sem exigir DATABASE_URL."""

    app_env: str = Field(default="staging")
    log_level: str = Field(default="INFO")

    @model_validator(mode="after")
    def validate_staging_requirements(self) -> Self:
        if not self.has_llm_key:
            import warnings
            warnings.warn(
                "Chave do provedor de LLM não configurada — API rodará em modo degradado (sem chat/explain)",
                stacklevel=2,
            )
        return self


class ProdSettings(Settings):
    """Configurações para produção — validações estritas, falha rápida se mal configurado."""

    app_env: str = Field(default="production")
    log_level: str = Field(default="INFO")

    @model_validator(mode="after")
    def validate_prod_requirements(self) -> Self:
        errors: list[str] = []

        if not self.database_url:
            errors.append("DATABASE_URL é obrigatório em produção")

        if not self.has_llm_key:
            errors.append(
                "Chave do provedor de LLM é obrigatória em produção "
                "(defina OPENAI_API_KEY ou GROQ_API_KEY via secrets manager)"
            )

        if errors:
            raise ValueError(
                "Configuração de produção inválida:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        return self


_ENV_TO_CLASS: dict[str, type[Settings]] = {
    "development": DevSettings,
    "staging": StagingSettings,
    "production": ProdSettings,
}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Retorna a instância singleton de configurações (cached).

    A classe concreta é selecionada pelo valor de APP_ENV (lido diretamente
    do ambiente antes do pydantic — sem dependência circular).
    """
    env = os.getenv("APP_ENV", "development").lower()
    cls = _ENV_TO_CLASS.get(env, DevSettings)
    return cls()


settings = get_settings()
