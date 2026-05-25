"""FastAPI app entry point for the production T1D Companion service."""

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load .env before any app imports
_env = Path("/root/t1d/.env")
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.core.database import db_manager, get_settings
from app.t1d_companion.production.api import router as companion_router
from app.t1d_companion.production.config import CompanionConfig

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("t1d.companion")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB. Shutdown: dispose DB."""
    config = CompanionConfig.from_env()
    logger.info(f"Starting T1D Companion service (model={config.model})")
    db_manager.init_db(config.database_url)
    yield
    await db_manager.dispose()


app = FastAPI(
    title="T1D Companion API",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(companion_router)


# ── Middleware: request ID + timing ──
@app.middleware("http")
async def add_request_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    response.headers["X-Request-ID"] = str(uuid.uuid4())
    response.headers["X-Processing-Time-Ms"] = str(round(elapsed, 1))
    return response


# ── Global error handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "request_id": str(uuid.uuid4())},
    )


@app.get("/")
async def root():
    return {"service": "T1D Companion API", "version": "3.0.0", "status": "running"}


# ── Run with: uvicorn app.t1d_companion.production.main:app --host 0.0.0.0 --port 8000 ──