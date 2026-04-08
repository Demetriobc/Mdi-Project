"""
Configuração central da aplicação.

Usa pydantic-settings para carregar variáveis de ambiente com validação de tipos
e valores padrão. Um único objeto `settings` é instanciado e reutilizado em
todo o projeto — sem chamar os.getenv() espalhado pelo código.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
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
    app_name: str = Field(default="house-price-copilot")
    app_version: str = Field(default="0.1.0")
    log_level: str = Field(default="INFO")

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # ── LLM ───────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    openai_temperature: float = Field(default=0.3)
    openai_max_tokens: int = Field(default=1024)

    # ── RAG ───────────────────────────────────────────────────────────────────
    embedding_provider: str = Field(default="local")  # "local" | "openai"
    vectorstore_path: Path = Field(default=Path("artifacts/vectorstore"))
    knowledge_base_path: Path = Field(default=Path("data/knowledge_base"))
    rag_top_k: int = Field(default=4)

    # ── Artefatos ML ──────────────────────────────────────────────────────────
    model_path: Path = Field(default=Path("artifacts/model/house_price_model.joblib"))
    preprocessor_path: Path = Field(default=Path("artifacts/model/preprocessor.joblib"))
    metadata_path: Path = Field(default=Path("artifacts/model/metadata.json"))

    # ── Banco de dados ────────────────────────────────────────────────────────
    database_url: str = Field(default="")

    # ── UI ────────────────────────────────────────────────────────────────────
    api_base_url: str = Field(default="http://localhost:8000")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def has_openai_key(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key != "sk-...")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a instância singleton de configurações (cached)."""
    return Settings()


settings = get_settings()
