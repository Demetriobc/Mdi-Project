"""
Gerenciamento de conexão com o banco de dados.

Usa o padrão de session factory do SQLAlchemy 2.0.
O banco é completamente opcional — se DATABASE_URL não estiver configurada
ou for o placeholder do .env.example, todas as operações são no-op.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_engine = None
_SessionLocal = None


def _is_db_configured() -> bool:
    """Verifica se a DATABASE_URL está configurada e não é o placeholder."""
    url = settings.database_url
    return bool(
        url
        and not url.startswith("postgresql://user:password")
        and "localhost" not in url or _is_real_url(url)
    )


def _is_real_url(url: str) -> bool:
    return url.startswith("postgresql://") and "password@" not in url or (
        url.startswith("postgresql://") and "@" in url and len(url) > 40
    )


def get_engine() -> Any | None:
    """Retorna o engine SQLAlchemy, criando-o na primeira chamada."""
    global _engine

    if _engine is not None:
        return _engine

    url = settings.database_url
    if not url or url.startswith("postgresql://user:password"):
        return None

    try:
        _engine = create_engine(
            url,
            pool_pre_ping=True,       # testa a conexão antes de usar
            pool_size=5,
            max_overflow=10,
            pool_recycle=300,         # recicla conexões a cada 5min
            echo=False,
        )
        logger.info("Engine PostgreSQL criado.")
        return _engine
    except Exception as e:
        logger.error(f"Falha ao criar engine de banco: {e}")
        return None


def get_session_factory() -> sessionmaker | None:
    """Retorna a session factory, criando-a se necessário."""
    global _SessionLocal

    if _SessionLocal is not None:
        return _SessionLocal

    engine = get_engine()
    if engine is None:
        return None

    _SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,  # evita lazy loading após commit
    )
    return _SessionLocal


def get_db() -> Generator[Session | None, None, None]:
    """
    Dependency para injeção de sessão nos endpoints FastAPI.

    Uso:
        @router.post("/predict")
        def predict(db: Session = Depends(get_db)):
            ...

    Se o banco não estiver configurado, db=None e o endpoint
    deve lidar com isso (operação opcional).
    """
    factory = get_session_factory()
    if factory is None:
        yield None
        return

    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def db_available() -> bool:
    """Verifica se o banco está acessível (para health check)."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
