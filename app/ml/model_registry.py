"""Paths em settings + joblib/json — sem camadas extras."""

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


def save_model(model: Any, path: Path | None = None) -> Path:
    target = path or settings.model_path
    ensure_dir(target.parent)
    joblib.dump(model, target)
    logger.info("Modelo salvo em %s", target)
    return target


def save_preprocessor(preprocessor: Any, path: Path | None = None) -> Path:
    target = path or settings.preprocessor_path
    ensure_dir(target.parent)
    joblib.dump(preprocessor, target)
    logger.info("Preprocessor salvo em %s", target)
    return target


def save_metadata(metadata: dict[str, Any], path: Path | None = None) -> Path:
    target = path or settings.metadata_path
    ensure_dir(target.parent)
    metadata["saved_at"] = datetime.now(tz=timezone.utc).isoformat()
    with open(target, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logger.info("Metadados em %s", target)
    return target


def save_quantile_models(model_p10: Any, model_p90: Any) -> None:
    for model, path in (
        (model_p10, settings.model_p10_path),
        (model_p90, settings.model_p90_path),
    ):
        ensure_dir(path.parent)
        joblib.dump(model, path)
        logger.info("Quantil salvo em %s", path)


def save_house_price_artifacts(
    model: Any,
    preprocessor: Any,
    metadata: dict[str, Any],
    model_p10: Any | None = None,
    model_p90: Any | None = None,
) -> None:
    save_model(model)
    save_preprocessor(preprocessor)
    save_metadata(metadata)
    if model_p10 is not None and model_p90 is not None:
        save_quantile_models(model_p10, model_p90)


def load_model(path: Path | None = None) -> Any:
    target = path or settings.model_path
    _require_file(target, "Modelo")
    return joblib.load(target)


def load_preprocessor(path: Path | None = None) -> Any:
    target = path or settings.preprocessor_path
    _require_file(target, "Preprocessor")
    return joblib.load(target)


def load_metadata(path: Path | None = None) -> dict[str, Any]:
    target = path or settings.metadata_path
    _require_file(target, "Metadados")
    with open(target, encoding="utf-8") as f:
        return json.load(f)


def load_quantile_models() -> tuple[Any, Any] | tuple[None, None]:
    if not quantile_artifacts_exist():
        logger.warning("P10/P90 ausentes; intervalo de confiança desligado.")
        return None, None
    return joblib.load(settings.model_p10_path), joblib.load(settings.model_p90_path)


def artifacts_exist() -> bool:
    return (
        settings.model_path.exists()
        and settings.preprocessor_path.exists()
        and settings.metadata_path.exists()
    )


def quantile_artifacts_exist() -> bool:
    return settings.model_p10_path.exists() and settings.model_p90_path.exists()


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} não encontrado: {path}. Rode o treino antes.")
