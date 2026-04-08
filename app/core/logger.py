"""
Configuração centralizada de logging.

Usa o módulo padrão `logging` com formatação estruturada e colorida em
desenvolvimento. Em produção, emite JSON-like para facilitar ingestão
por ferramentas de observabilidade (Datadog, CloudWatch, Railway logs).
"""

import logging
import sys
from typing import Optional

from app.core.config import settings


_LOG_FORMAT_DEV = (
    "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
)
_LOG_FORMAT_PROD = (
    "%(asctime)s %(levelname)s %(name)s %(message)s"
)


def _build_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    fmt = _LOG_FORMAT_DEV if not settings.is_production else _LOG_FORMAT_PROD
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    return handler


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Retorna um logger configurado para o módulo informado.

    Uso:
        from app.core.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Mensagem")
    """
    logger = logging.getLogger(name or "house_price_copilot")

    if not logger.handlers:
        logger.addHandler(_build_handler())
        logger.setLevel(settings.log_level.upper())
        logger.propagate = False

    return logger


def configure_root_logger() -> None:
    """
    Configura o logger raiz da aplicação.
    Deve ser chamado uma vez na inicialização da API.
    """
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    # Silenciar loggers verbosos de bibliotecas externas
    for noisy in ("httpx", "httpcore", "openai", "faiss"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if not root.handlers:
        root.addHandler(_build_handler())
