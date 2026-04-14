# -----------------------------------------------------------------------------
# Estágio 1: dependências de build + download do dataset + treino ML + índice RAG
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data
COPY scripts ./scripts

ARG KC_HOUSE_DATA_URL=https://storage.googleapis.com/mledu-datasets/kc_house_data.csv
ENV KC_HOUSE_DATA_URL=${KC_HOUSE_DATA_URL}
ENV PYTHONUNBUFFERED=1

RUN mkdir -p data/raw \
    && python scripts/download_kc_house_data.py \
    && python -m app.ml.train \
    && python -m app.rag.build_kb

# -----------------------------------------------------------------------------
# Estágio 2: só runtime (sem gcc); artefatos copiados do builder
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data/knowledge_base ./data/knowledge_base
COPY --from=builder /app/artifacts ./artifacts

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT}"]
