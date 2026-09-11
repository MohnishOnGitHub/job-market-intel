from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.analytics import router as analytics_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.matches import router as matches_router
from app.api.routes.matching import router as matching_router
from app.api.routes.skills import router as skills_router
from app.api.routes.status import router as status_router
from app.core.config import get_settings
from app.core.exceptions import AppError

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Job Market Intel",
        description=(
            "Job-market intelligence and résumé matching. "
            "Analytics use SQL aggregates over active PostgreSQL jobs. "
            "Matching exposes a pairwise TF-IDF baseline (`POST /upload-resume`) "
            "and a structured hybrid ranker (`POST /api/v1/matches`). "
            "hashing-v1 is lexical hashing retrieval, not semantic embeddings."
        ),
        version="0.6.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            return await http_exception_handler(request, exc)
        if isinstance(exc, RequestValidationError):
            return await request_validation_exception_handler(request, exc)
        logging.getLogger("app").exception("unhandled_error")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(matching_router)
    app.include_router(skills_router, prefix="/api/v1")
    app.include_router(status_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(matches_router, prefix="/api/v1")

    if FRONTEND_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    app.state.settings = settings
    return app


app = create_app()
