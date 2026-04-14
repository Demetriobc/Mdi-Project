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
from app.db.init_db import init_db
from app.db.session import db_available
from app.ml.model_registry import artifacts_exist
from app.rag.retriever import vectorstore_exists

configure_root_logger()
logger = get_logger(__name__)


def _cors_allow_origins() -> list[str]:
    if not settings.is_production:
        return ["*"]
    raw = (settings.cors_origins or "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    if settings.api_base_url and not settings.api_base_url.startswith("http://localhost"):
        return [settings.api_base_url.rstrip("/")]
    return ["*"]


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

    # Inicializa banco (cria tabelas + seed zipcodes)
    init_db()
    if db_available():
        logger.info("PostgreSQL: conectado")
    else:
        logger.warning("PostgreSQL: nao configurado — logs de predicao desabilitados")

    logger.info(f"API rodando em http://{settings.api_host}:{settings.api_port}")
    logger.info(f"Docs: http://localhost:{settings.api_port}/docs")

    yield

    logger.info("API encerrada.")


# ── Aplicação ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="madeinweb-teste API",
    description=(
        "API para previsão e explicação de preços de imóveis em King County, WA. "
        "Combina XGBoost (ML) + RAG (FAISS) + LLM para gerar previsões "
        "com explicações em linguagem natural."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS ──────────────────────────────────────────────────────────────────────

_origins = _cors_allow_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # Com allow_origins=["*"] o Starlette exige allow_credentials=False
    allow_credentials=False if _origins == ["*"] else True,
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
