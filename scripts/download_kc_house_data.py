"""
Baixa kc_house_data.csv para data/raw/ (Docker build / CI).

A URL do Google (mledu-datasets) costuma devolver 403 para clientes sem browser UA.
Ordem: KC_HOUSE_DATA_URL / argv → mirrors públicos (GitHub raw) → última tentativa Google com UA.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "data" / "raw" / "kc_house_data.csv"

# Mirrors estáveis (schema id,date,price,zipcode,... — mesmo do curso / Kaggle).
DEFAULT_URL_CHAIN: list[str] = [
    "https://raw.githubusercontent.com/Shreyas3108/house-price-prediction/master/kc_house_data.csv",
    "https://raw.githubusercontent.com/karan-shah/usa-housing-dataset/dev/kc_house_data.csv",
    "https://storage.googleapis.com/mledu-datasets/kc_house_data.csv",
]

REQUIRED_COLUMNS = ("id", "date", "price", "zipcode", "sqft_living")

# Alguns CDNs bloqueiam o UA default de Python.
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; house-price-copilot/1.0; "
        "+https://github.com/) Python-urllib"
    ),
    "Accept": "*/*",
}


def _download_one(url: str, dest: Path, timeout_sec: int = 120) -> None:
    req = Request(url, headers=HTTP_HEADERS, method="GET")
    with urlopen(req, timeout=timeout_sec) as resp:
        data = resp.read()
    dest.write_bytes(data)


def _urls_to_try() -> list[str]:
    explicit = (
        (sys.argv[1] if len(sys.argv) > 1 else None)
        or os.environ.get("KC_HOUSE_DATA_URL", "").strip()
    )
    if explicit:
        return [explicit] + [u for u in DEFAULT_URL_CHAIN if u != explicit]
    return list(DEFAULT_URL_CHAIN)


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    for url in _urls_to_try():
        print(f"Tentando: {url}", flush=True)
        try:
            _download_one(url, OUT_PATH)
        except HTTPError as e:
            msg = f"{e.code} {e.reason}"
            errors.append(f"{url} -> {msg}")
            print(f"  falhou: {msg}", flush=True)
            continue
        except URLError as e:
            errors.append(f"{url} -> {e}")
            print(f"  falhou: {e}", flush=True)
            continue

        if OUT_PATH.stat().st_size < 10_000:
            errors.append(f"{url} -> arquivo muito pequeno")
            print("  falhou: arquivo muito pequeno", flush=True)
            continue

        header = OUT_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            errors.append(f"{url} -> colunas faltando: {missing}")
            print(f"  falhou: header inválido ({missing})", flush=True)
            continue

        print(f"OK -> {OUT_PATH} ({OUT_PATH.stat().st_size // 1024} KB)", flush=True)
        return

    print("ERRO: todas as URLs falharam.", file=sys.stderr)
    for line in errors:
        print(f"  - {line}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
