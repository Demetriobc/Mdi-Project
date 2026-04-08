"""
Registro de artefatos de modelo.

Centraliza a lógica de persistência: salvar e carregar o modelo,
o preprocessor e os metadados JSON. Qualquer módulo que precise
de artefatos chama este registry — nunca acessa `artifacts/` diretamente.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from app.core.config import settings
from app.core.logger import get_logger
from app.core.utils import ensure_dir

logger = get_logger(__name__)


# ── Salvamento ────────────────────────────────────────────────────────────────

def save_model(model: Any, path: Path | None = None) -> Path:
    """Salva o modelo treinado com joblib."""
    target = path or settings.model_path
    ensure_dir(target.parent)
    joblib.dump(model, target)
    logger.info(f"Modelo salvo em: {target}")
    return target


def save_preprocessor(preprocessor: Any, path: Path | None = None) -> Path:
    """Salva o pipeline de preprocessamento com joblib."""
    target = path or settings.preprocessor_path
    ensure_dir(target.parent)
    joblib.dump(preprocessor, target)
    logger.info(f"Preprocessor salvo em: {target}")
    return target


def save_metadata(metadata: dict[str, Any], path: Path | None = None) -> Path:
    """Salva os metadados do modelo como JSON."""
    target = path or settings.metadata_path
    ensure_dir(target.parent)

    metadata["saved_at"] = datetime.now(tz=timezone.utc).isoformat()

    with open(target, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(f"Metadados salvos em: {target}")
    return target


def save_all(
    model: Any,
    preprocessor: Any,
    metadata: dict[str, Any],
) -> None:
    """Salva todos os artefatos de uma vez."""
    save_model(model)
    save_preprocessor(preprocessor)
    save_metadata(metadata)
    logger.info("Todos os artefatos foram salvos com sucesso.")


# ── Carregamento ──────────────────────────────────────────────────────────────

def load_model(path: Path | None = None) -> Any:
    """
    Carrega o modelo treinado.

    Raises:
        FileNotFoundError: se o artefato não existir (modelo não treinado).
    """
    target = path or settings.model_path
    _assert_exists(target, "Modelo")
    model = joblib.load(target)
    logger.info(f"Modelo carregado de: {target}")
    return model


def load_preprocessor(path: Path | None = None) -> Any:
    """Carrega o pipeline de preprocessamento."""
    target = path or settings.preprocessor_path
    _assert_exists(target, "Preprocessor")
    preprocessor = joblib.load(target)
    logger.info(f"Preprocessor carregado de: {target}")
    return preprocessor


def load_metadata(path: Path | None = None) -> dict[str, Any]:
    """Carrega os metadados do modelo."""
    target = path or settings.metadata_path
    _assert_exists(target, "Metadados")
    with open(target, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    return metadata


def artifacts_exist() -> bool:
    """Verifica se todos os artefatos necessários estão presentes."""
    return (
        settings.model_path.exists()
        and settings.preprocessor_path.exists()
        and settings.metadata_path.exists()
    )


# ── Utilitário interno ────────────────────────────────────────────────────────

def _assert_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"{label} não encontrado em: {path}\n"
            "Execute `make train` para gerar os artefatos."
        )
