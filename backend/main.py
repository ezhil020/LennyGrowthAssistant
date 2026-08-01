"""
main.py — FastAPI application entry point.

Registers middleware, exception handlers, and all API routers.
Runs config validation and logging setup on startup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.logging_config import configure_logging
from backend.middleware.exception_handler import (
    global_exception_handler,
    runtime_error_handler,
    value_error_handler,
)
from backend.middleware.logging_middleware import LoggingMiddleware
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.middleware.request_id import RequestIDMiddleware
from backend.middleware.timing_middleware import TimingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — runs once on startup and shutdown."""
    configure_logging()
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info(
        "app_startup",
        provider=settings.active_llm_provider,
        embedding=settings.active_embedding_model,
        retrieval=settings.retrieval_mode,
    )
    yield
    logger.info("app_shutdown")


app = FastAPI(
    title="Lenny Growth Assistant API",
    description="AI-powered Q&A, Ship30for30 content generation, and artifact creation grounded in Lenny's Podcast.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Middleware (applied in reverse registration order — last added = outermost) ──
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(RuntimeError, runtime_error_handler)

# ── API Routers (all versioned under /api/v1) ─────────────────────────────────
from backend.api.v1 import sessions, chat, artifacts, config_api, health, ingestion

API_PREFIX = "/api/v1"
app.include_router(sessions.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(artifacts.router, prefix=API_PREFIX)
app.include_router(config_api.router, prefix=API_PREFIX)
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(ingestion.router, prefix=API_PREFIX)


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "Lenny Growth Assistant API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/v1/health",
    }
