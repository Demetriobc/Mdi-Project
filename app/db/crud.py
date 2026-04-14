"""
Operações CRUD do banco de dados.

Cada função recebe uma Session e retorna um resultado tipado.
Todas são no-op silenciosas se db=None (banco não configurado).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.db.models import ChatMessage, PredictionLog, ZipcodeStats

logger = get_logger(__name__)


# ── Predictions ───────────────────────────────────────────────────────────────

def log_prediction(
    db: Session | None,
    house_input: dict,
    predicted_price: float,
    zipcode_median_price: float | None = None,
    price_vs_median_pct: float | None = None,
) -> PredictionLog | None:
    """
    Salva uma predição no banco.

    Retorna o registro criado (com id preenchido) ou None se o banco
    não estiver disponível.
    """
    if db is None:
        return None

    try:
        record = PredictionLog(
            zipcode=house_input.get("zipcode", ""),
            sqft_living=house_input.get("sqft_living"),
            bedrooms=house_input.get("bedrooms"),
            bathrooms=house_input.get("bathrooms"),
            grade=house_input.get("grade"),
            condition=house_input.get("condition"),
            floors=house_input.get("floors"),
            waterfront=house_input.get("waterfront"),
            view=house_input.get("view"),
            yr_built=house_input.get("yr_built"),
            yr_renovated=house_input.get("yr_renovated"),
            sqft_lot=house_input.get("sqft_lot"),
            lat=house_input.get("lat"),
            long=house_input.get("long"),
            predicted_price=predicted_price,
            zipcode_median_price=zipcode_median_price,
            price_vs_median_pct=price_vs_median_pct,
        )
        db.add(record)
        db.flush()  # gera o id sem fechar a transação
        logger.debug(f"Predição logada: id={record.id} zipcode={record.zipcode}")
        return record

    except Exception as e:
        logger.error(f"Erro ao logar predição: {e}")
        return None


def get_recent_predictions(
    db: Session | None,
    limit: int = 50,
    zipcode: str | None = None,
) -> list[PredictionLog]:
    """Retorna as predições mais recentes, opcionalmente filtradas por zipcode."""
    if db is None:
        return []

    try:
        q = db.query(PredictionLog).order_by(PredictionLog.created_at.desc())
        if zipcode:
            q = q.filter(PredictionLog.zipcode == zipcode)
        return q.limit(limit).all()
    except Exception as e:
        logger.error(f"Erro ao buscar predições: {e}")
        return []


def get_prediction_stats(db: Session | None) -> dict:
    """
    Retorna estatísticas agregadas das predições para o health check / dashboard.
    """
    if db is None:
        return {}

    try:
        from sqlalchemy import func

        total = db.query(func.count(PredictionLog.id)).scalar() or 0
        avg_price = db.query(func.avg(PredictionLog.predicted_price)).scalar()
        top_zipcodes = (
            db.query(PredictionLog.zipcode, func.count(PredictionLog.id).label("n"))
            .group_by(PredictionLog.zipcode)
            .order_by(func.count(PredictionLog.id).desc())
            .limit(5)
            .all()
        )
        return {
            "total_predictions": total,
            "avg_predicted_price": round(avg_price, 2) if avg_price else None,
            "top_zipcodes": [{"zipcode": z, "count": n} for z, n in top_zipcodes],
        }
    except Exception as e:
        logger.error(f"Erro ao calcular stats: {e}")
        return {}


# ── Zipcode Stats ─────────────────────────────────────────────────────────────

def get_zipcode_median(db: Session | None, zipcode: str) -> float | None:
    """Retorna o preço mediano de um zipcode direto do banco."""
    if db is None:
        return None

    try:
        record = db.query(ZipcodeStats).filter(ZipcodeStats.zipcode == zipcode).first()
        return record.median_price if record else None
    except Exception as e:
        logger.error(f"Erro ao buscar mediana do zipcode {zipcode}: {e}")
        return None


def get_zipcode_info(db: Session | None, zipcode: str) -> ZipcodeStats | None:
    """Retorna informações completas de um zipcode."""
    if db is None:
        return None

    try:
        return db.query(ZipcodeStats).filter(ZipcodeStats.zipcode == zipcode).first()
    except Exception as e:
        logger.error(f"Erro ao buscar info do zipcode {zipcode}: {e}")
        return None


def upsert_zipcode_stats(
    db: Session | None,
    zipcode: str,
    median_price: float,
    city: str | None = None,
    neighborhood: str | None = None,
    price_tier: str | None = None,
    avg_grade: float | None = None,
    notes: str | None = None,
) -> None:
    """Insere ou atualiza estatísticas de um zipcode."""
    if db is None:
        return

    try:
        record = db.query(ZipcodeStats).filter(ZipcodeStats.zipcode == zipcode).first()
        if record:
            record.median_price = median_price
            if city:
                record.city = city
            if neighborhood:
                record.neighborhood = neighborhood
            if price_tier:
                record.price_tier = price_tier
            if avg_grade:
                record.avg_grade = avg_grade
            if notes:
                record.notes = notes
        else:
            db.add(ZipcodeStats(
                zipcode=zipcode,
                median_price=median_price,
                city=city,
                neighborhood=neighborhood,
                price_tier=price_tier,
                avg_grade=avg_grade,
                notes=notes,
            ))
    except Exception as e:
        logger.error(f"Erro ao upsert zipcode {zipcode}: {e}")


# ── Chat ──────────────────────────────────────────────────────────────────────

def save_chat_message(
    db: Session | None,
    session_id: str,
    role: str,
    content: str,
    sources: list[str] | None = None,
    prediction_id: int | None = None,
) -> ChatMessage | None:
    """Persiste uma mensagem do chat no banco."""
    if db is None:
        return None

    try:
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sources=json.dumps(sources) if sources else None,
            prediction_id=prediction_id,
        )
        db.add(msg)
        db.flush()
        return msg
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem de chat: {e}")
        return None


def get_chat_history(
    db: Session | None,
    session_id: str,
    limit: int = 20,
) -> list[dict]:
    """
    Retorna o histórico de chat de uma sessão no formato esperado pelo LLM.
    """
    if db is None:
        return []

    try:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in messages]
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de chat: {e}")
        return []
