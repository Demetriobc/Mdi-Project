"""
Configuração centralizada de logging.

Em desenvolvimento: formato legível com timestamp, nível e módulo.
Em produção: JSON estruturado via python-json-logger para ingestão
no Datadog, CloudWatch, Railway Logs, etc.

Uso:
    from app.core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Modelo carregado", extra={"model_version": "1.2.0"})
"""

import logging
import sys
from typing import Optional

from app.core.config import settings

_LOG_FORMAT_DEV = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"


def _build_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)

    if settings.is_production:
        try:
            from pythonjsonlogger import jsonlogger

            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
                rename_fields={"levelname": "level", "asctime": "timestamp"},
            )
        except ImportError:
            # Fallback gracioso se python-json-logger não estiver instalado
            formatter = logging.Formatter(_LOG_FORMAT_DEV, datefmt="%Y-%m-%d %H:%M:%S")
    else:
        formatter = logging.Formatter(_LOG_FORMAT_DEV, datefmt="%Y-%m-%d %H:%M:%S")

    handler.setFormatter(formatter)
    return handler


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Retorna um logger configurado para o módulo informado.

    Em produção emite JSON. Em desenvolvimento emite texto legível.
    Cada módulo obtém seu próprio logger — rastreabilidade de origem preservada.
    """
    logger = logging.getLogger(name or "madeinweb_teste")

    if not logger.handlers:
        logger.addHandler(_build_handler())
        logger.setLevel(settings.log_level.upper())
        logger.propagate = False

    return logger


def configure_root_logger() -> None:
    """
    Configura o logger raiz da aplicação.
    Deve ser chamado uma vez na inicialização da API (lifespan).
    """
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    # Silenciar loggers verbosos de bibliotecas externas
    for noisy in ("httpx", "httpcore", "openai", "faiss"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if not root.handlers:
        root.addHandler(_build_handler())
