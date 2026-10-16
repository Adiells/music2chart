"""FastAPI application factory, CORS configuration, and global error handling."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config.settings import get_settings
from src.api.routes import preview_router, task_manager
from src.api.routes import router as chart_router
from src.api.schemas import HealthResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context: initialize storage, background cleanup, and resources."""
    settings = get_settings()
    settings.ensure_directories()
    logger.info("Application starting up: %s (env=%s)", settings.APP_NAME, settings.APP_ENV)

    stop_event = asyncio.Event()

    async def periodic_cleanup() -> None:
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=float(settings.CLEANUP_INTERVAL_SECONDS)
                )
                break
            except TimeoutError:
                try:
                    expired = task_manager.cleanup_expired_tasks(
                        ttl_seconds=float(settings.TASK_TTL_SECONDS)
                    )
                    if expired:
                        logger.info(
                            "Periodic cleanup purged %d expired task(s): %s", len(expired), expired
                        )
                except Exception as exc:
                    logger.warning("Error during periodic task cleanup: %s", exc)

    cleanup_task = asyncio.create_task(periodic_cleanup())
    try:
        yield
    finally:
        logger.info("Application shutting down.")
        stop_event.set()
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


def create_app(frontend_dist: Path | str | None = None) -> FastAPI:
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
    origins = settings.ALLOWED_ORIGINS
    allow_creds = "*" not in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https?://([a-zA-Z0-9-]+\.)*adiels\.me(:[0-9]+)?",
        allow_credentials=allow_creds,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Security Headers Middleware
    # -----------------------------------------------------------------------
    @app.middleware("http")
    async def add_security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

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
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception: %s", exc)
        origin = request.headers.get("origin")
        headers: dict[str, str] = {}
        if origin:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Internal server error: {exc}"},
            headers=headers,
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
    # Web UI Route & Frontend Static Files
    # -----------------------------------------------------------------------
    if frontend_dist is not None:
        frontend_dist_dir = Path(frontend_dist)
    else:
        explicit_dist = Path("/home/adiel/Projects/music2chart/frontend/dist")
        relative_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
        frontend_dist_dir = explicit_dist if explicit_dist.is_dir() else relative_dist

    fallback_index_file = Path(__file__).parent / "static" / "index.html"

    # Serve compiled frontend assets if available
    if frontend_dist_dir.is_dir() and (frontend_dist_dir / "assets").is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(frontend_dist_dir / "assets")),
            name="frontend_assets",
        )
    else:
        # Fallback route to serve assets if frontend/dist/assets is compiled dynamically
        @app.get("/assets/{file_path:path}", include_in_schema=False)
        async def serve_dynamic_assets(file_path: str) -> FileResponse:
            assets_dir = (frontend_dist_dir / "assets").resolve()
            clean_path = file_path.replace("\\", "/").lstrip("/")
            target = (assets_dir / clean_path).resolve()
            if not target.is_relative_to(assets_dir):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied.",
                )
            if frontend_dist_dir.is_dir() and target.is_file():
                return FileResponse(target)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset '{file_path}' not found.",
            )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def serve_index() -> HTMLResponse:
        """Serve the interactive web interface with live progress tracking."""
        frontend_index = frontend_dist_dir / "index.html"
        if frontend_dist_dir.is_dir() and frontend_index.is_file():
            return HTMLResponse(content=frontend_index.read_text(encoding="utf-8"))
        if fallback_index_file.exists():
            return HTMLResponse(content=fallback_index_file.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>music2chart API</h1>")

    # -----------------------------------------------------------------------
    # Router Mounts
    # -----------------------------------------------------------------------
    app.include_router(chart_router)
    app.include_router(preview_router)

    return app


app = create_app()
