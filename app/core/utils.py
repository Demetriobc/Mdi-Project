"""
Utilitários genéricos reutilizáveis em todo o projeto.

Funções pequenas e sem estado que não pertencem a nenhuma camada específica.
"""

import json
import time
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def load_json(path: Path) -> dict[str, Any]:
    """Carrega um arquivo JSON e retorna como dicionário."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict[str, Any], path: Path) -> None:
    """Serializa um dicionário para JSON no caminho informado."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.debug(f"JSON salvo em: {path}")


def ensure_dir(path: Path) -> Path:
    """Garante que o diretório existe, criando-o se necessário."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_currency(value: float, prefix: str = "US$") -> str:
    """Formata um valor numérico como moeda legível."""
    return f"{prefix} {value:,.0f}"


def timer(func):
    """
    Decorador simples para medir tempo de execução de funções.

    Uso:
        @timer
        def minha_funcao(): ...
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__name__} executado em {elapsed:.3f}s")
        return result

    return wrapper
