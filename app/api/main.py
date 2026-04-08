"""
Ponto de entrada da API FastAPI.

Configura CORS, registra os roteadores, define handlers de exceção
e verifica a disponibilidade dos artefatos no startup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, health, predict
from app.core.config import settings
from app.core.logger import configure_root_logger, get_logger
from app.ml.model_registry import artifacts_exist
from app.rag.retriever import vectorstore_exists

configure_root_logger()
logger = get_logger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executa verificações de saúde no startup.

    Não bloqueia a inicialização mesmo que artefatos estejam ausentes —
    o /health endpoint reportará o estado e os endpoints falharão
    com 503 adequados ao invés de crashar o servidor.
    """
    logger.info("=" * 55)
    logger.info(f"Iniciando {settings.app_name} v{settings.app_version}")
    logger.info("=" * 55)

    if artifacts_exist():
        logger.info("Modelo ML: pronto")
    else:
        logger.warning("Modelo ML: nao encontrado (execute make train)")

    if vectorstore_exists():
        logger.info("RAG vectorstore: pronto")
    else:
        logger.warning("RAG vectorstore: nao encontrado (execute make build-kb)")

    if settings.has_openai_key:
        logger.info(f"LLM: configurado ({settings.openai_model})")
    else:
        logger.warning("LLM: sem API key — chat em modo degradado")

    logger.info(f"API rodando em http://{settings.api_host}:{settings.api_port}")
    logger.info("Docs: http://localhost:8000/docs")

    yield

    logger.info("API encerrada.")


# ── Aplicação ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="House Price Copilot API",
    description=(
        "API para previsão e explicação de preços de imóveis em King County, WA. "
        "Combina XGBoost (ML) + RAG (FAISS) + LLM (OpenAI) para gerar previsões "
        "precisas com explicações em linguagem natural."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else [settings.api_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc), "hint": "Execute make train e make build-kb primeiro."},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


# ── Roteadores ────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(predict.router)
app.include_router(chat.router)


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
