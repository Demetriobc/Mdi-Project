"""
Baixa kc_house_data.csv para data/raw/ (Docker build / CI).

URL padrão: cópia pública usada no curso de ML do Google (mesmo schema KC House).
Sobrescreva com KC_HOUSE_DATA_URL ou primeiro argumento na linha de comando.

Uso:
  python scripts/download_kc_house_data.py
  python scripts/download_kc_house_data.py https://exemplo.com/kc_house_data.csv
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

# Mesmo dataset King County; troque se a Google desligar o bucket.
DEFAULT_URL = "https://storage.googleapis.com/mledu-datasets/kc_house_data.csv"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "data" / "raw" / "kc_house_data.csv"

REQUIRED_COLUMNS = ("id", "date", "price", "zipcode", "sqft_living")


def main() -> None:
    url = (
        (sys.argv[1] if len(sys.argv) > 1 else None)
        or os.environ.get("KC_HOUSE_DATA_URL")
        or DEFAULT_URL
    ).strip()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Download: {url}\nDestino: {OUT_PATH}", flush=True)

    try:
        urlretrieve(url, OUT_PATH)
    except URLError as e:
        print(f"ERRO ao baixar: {e}", file=sys.stderr)
        sys.exit(1)

    if not OUT_PATH.exists() or OUT_PATH.stat().st_size < 10_000:
        print("ERRO: arquivo baixado vazio ou pequeno demais.", file=sys.stderr)
        sys.exit(1)

    header = OUT_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        print(f"ERRO: CSV sem colunas esperadas {missing}. Header: {header[:200]}", file=sys.stderr)
        sys.exit(1)

    print(f"OK — {OUT_PATH.stat().st_size // 1024} KB", flush=True)


if __name__ == "__main__":
    main()
