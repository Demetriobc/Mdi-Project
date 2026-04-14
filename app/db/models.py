"""
Modelos SQLAlchemy do projeto.

Três tabelas:
  predictions_log  → audit trail de cada predição feita
  zipcode_stats    → referência de mercado por zipcode (seed do treino + KB)
  chat_messages    → histórico persistido de conversas

Design: as tabelas são opcionais — se DATABASE_URL não estiver configurada,
o sistema funciona normalmente sem banco (modo degradado).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Predições ─────────────────────────────────────────────────────────────────

class PredictionLog(Base):
    """
    Registra cada predição realizada pela API.

    Usado para:
    - Auditoria e rastreabilidade
    - Monitoramento de drift (distribuição de inputs ao longo do tempo)
    - Análise de uso (quais zipcodes são mais consultados)
    - Dataset para futuros experimentos
    """

    __tablename__ = "predictions_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Inputs do imóvel
    zipcode: Mapped[str] = mapped_column(String(5), index=True, nullable=False)
    sqft_living: Mapped[int] = mapped_column(Integer, nullable=False)
    bedrooms: Mapped[int] = mapped_column(Integer, nullable=False)
    bathrooms: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    condition: Mapped[int] = mapped_column(Integer, nullable=False)
    floors: Mapped[float] = mapped_column(Float, nullable=True)
    waterfront: Mapped[int] = mapped_column(Integer, nullable=True)
    view: Mapped[int] = mapped_column(Integer, nullable=True)
    yr_built: Mapped[int] = mapped_column(Integer, nullable=True)
    yr_renovated: Mapped[int] = mapped_column(Integer, nullable=True)
    sqft_lot: Mapped[int] = mapped_column(Integer, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=True)
    long: Mapped[float] = mapped_column(Float, nullable=True)

    # Outputs
    predicted_price: Mapped[float] = mapped_column(Float, nullable=False)
    zipcode_median_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_vs_median_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relacionamento com chat
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<PredictionLog id={self.id} zipcode={self.zipcode} "
            f"price=${self.predicted_price:,.0f}>"
        )


# ── Referência de mercado ─────────────────────────────────────────────────────

class ZipcodeStats(Base):
    """
    Estatísticas de mercado por zipcode.

    Populada automaticamente no startup a partir de duas fontes:
    1. artifacts/model/metadata.json → medianas calculadas do treino
    2. data/knowledge_base/zipcode_insights.csv → contexto qualitativo

    Fonte principal para enriquecer as respostas da API com contexto
    de mercado (substitui o lookup em metadata.json).
    """

    __tablename__ = "zipcode_stats"

    zipcode: Mapped[str] = mapped_column(String(5), primary_key=True)
    median_price: Mapped[float] = mapped_column(Float, nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avg_grade: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ZipcodeStats {self.zipcode} median=${self.median_price:,.0f}>"


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage(Base):
    """
    Mensagem individual de uma conversa.

    Cada sessão de chat é identificada por um `session_id` (UUID gerado
    pelo cliente Streamlit e persistido em session_state).
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)   # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list de fontes

    # FK opcional para a predição que originou a conversa
    prediction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("predictions_log.id"), nullable=True, index=True
    )
    prediction: Mapped["PredictionLog | None"] = relationship(back_populates="chat_messages")

    def __repr__(self) -> str:
        return f"<ChatMessage session={self.session_id[:8]} role={self.role}>"
