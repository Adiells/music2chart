"""FastAPI application factory, CORS configuration, and global error handling."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from config.settings import get_settings
from src.api.routes import router as chart_router
from src.api.schemas import HealthResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context: initialize storage and resources."""
    settings = get_settings()
    settings.ensure_directories()
    logger.info("Application starting up: %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    yield
    logger.info("Application shutting down.")


def create_app() -> FastAPI:
    """Construct and configure FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="music2chart API",
        description=(
            "Automated high-fidelity pipeline converting raw audio tracks into playable "
            "Clone Hero charts (.chart) and binary packages (.sng)."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # CORS Middleware
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Global Exception Handlers
    # -----------------------------------------------------------------------
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected internal server error occurred."},
        )

    # -----------------------------------------------------------------------
    # Health Check Endpoints
    # -----------------------------------------------------------------------
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["System"],
        summary="Service liveness and health probe",
    )
    @app.get(
        "/api/v1/health",
        response_model=HealthResponse,
        tags=["System"],
        summary="API v1 health probe",
    )
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="ok",
            app_name=settings.APP_NAME,
            version="0.1.0",
        )

    # -----------------------------------------------------------------------
    # Web UI Route
    # -----------------------------------------------------------------------
    index_file = Path(__file__).parent / "static" / "index.html"

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def serve_index() -> HTMLResponse:
        """Serve the interactive web interface with live progress tracking."""
        if index_file.exists():
            return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>music2chart API</h1>")

    # -----------------------------------------------------------------------
    # Router Mounts
    # -----------------------------------------------------------------------
    app.include_router(chart_router)

    return app


app = create_app()
