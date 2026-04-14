.PHONY: help install train build-kb api ui test lint format clean docker-build docker-up docker-down

# ── Configuração ──────────────────────────────────────────────────────────────
PYTHON     = python
PIP        = pip
UVICORN    = uvicorn
STREAMLIT  = streamlit
API_MODULE = app.api.main:app
UI_MODULE  = app/ui/streamlit_app.py

help:  ## Mostra os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Ambiente ──────────────────────────────────────────────────────────────────
install:  ## Instala as dependências do projeto
	$(PIP) install -r requirements.txt

# ── Machine Learning ──────────────────────────────────────────────────────────
train:  ## Treina o modelo e salva os artefatos em artifacts/model/
	$(PYTHON) -m app.ml.train

build-kb:  ## Constrói a knowledge base e o índice FAISS
	$(PYTHON) -m app.rag.build_kb

# ── Serviços ──────────────────────────────────────────────────────────────────
api:  ## Inicia a API FastAPI (porta 8001)
	$(UVICORN) $(API_MODULE) --reload --host 0.0.0.0 --port 8001

ui:  ## Inicia a interface Streamlit (porta 8501)
	$(STREAMLIT) run $(UI_MODULE)

# ── Qualidade ─────────────────────────────────────────────────────────────────
test:  ## Executa os testes com pytest
	$(PYTHON) -m pytest tests/ -v

lint:  ## Verifica o código com ruff
	ruff check app/ tests/

format:  ## Formata o código com ruff
	ruff format app/ tests/

# ── Docker ────────────────────────────────────────────────────────────────────
docker-build:  ## Constrói a imagem Docker
	docker-compose build

docker-build-api:  ## Imagem só da API (treino + RAG dentro do build; demora vários minutos)
	docker build -t house-price-copilot-api .

docker-build-frontend:  ## Imagem do React (passa a URL da API)
	docker build -f frontend/Dockerfile ./frontend -t house-price-copilot-ui \
		--build-arg VITE_API_BASE_URL=$(VITE_API_BASE_URL)

docker-up:  ## Sobe os containers em background
	docker-compose up -d

docker-down:  ## Para e remove os containers
	docker-compose down

# ── Limpeza ───────────────────────────────────────────────────────────────────
clean:  ## Remove caches e arquivos temporários
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
