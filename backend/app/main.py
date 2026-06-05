import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exception_handlers import register_handlers
from app.core.input_sanitizer import InputSanitizerMiddleware
from app.core.observability import (
    PROCESS_TIME_HEADER,
    REQUEST_ID_HEADER,
    capture_exception,
    configure_logging,
    init_error_tracking,
    metrics_snapshot,
    record_request,
)
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.seed import seed_admin, seed_management_users
from app.db.session import AsyncSessionLocal
import app.models  # noqa: F401 - ensure all models are registered

configure_logging(settings.ENVIRONMENT)
init_error_tracking(settings.ERROR_TRACKING_DSN, settings.ENVIRONMENT)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.PROJECT_NAME, settings.VERSION)
    logger.info("Automatic table creation disabled; use Alembic migrations for schema changes")

    try:
        async with AsyncSessionLocal() as db:
            await seed_admin(db)
        async with AsyncSessionLocal() as db:
            await seed_management_users(db)
        from app.db.seed_finance import seed_finance_data
        async with AsyncSessionLocal() as db:
            await seed_finance_data(db)
        if settings.SEED_DEMO_DATA:
            from app.db.seed_production import seed_production_data
            async with AsyncSessionLocal() as db:
                await seed_production_data(db)
            from app.db.seed_inventory import seed_inventory_data
            async with AsyncSessionLocal() as db:
                await seed_inventory_data(db)
        logger.info("Seed completed")
    except Exception:
        logger.exception("Seed failed; admin user may not exist yet")

    yield

    logger.info("Shutting down %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "## FMCG ERP REST API\n\n"
        "Full-suite enterprise resource planning API for fast-moving consumer goods companies. "
        "Covers inventory, sales, procurement, manufacturing, finance, HR, quality, CRM, "
        "logistics, reporting, and notifications.\n\n"
        "### Authentication\n"
        "All protected endpoints require a Bearer token obtained from `POST /api/v1/auth/login`. "
        "Include the token as `Authorization: Bearer <token>`.\n\n"
        "### Permissions\n"
        "Access is role-based. Each endpoint declares the required permission code "
        "(e.g. `inventory.view`, `sales.create`). See `GET /api/v1/modules/manifest` "
        "for the full permission code registry.\n\n"
        "### Rate Limits\n"
        "Default: 1000 requests/minute per authenticated user. "
        "Bulk endpoints may have lower individual limits.\n\n"
        "### Environments\n"
        "- Development: `http://localhost:8000`\n"
        "- Staging/Production: configured via `BACKEND_CORS_ORIGINS`"
    ),
    contact={
        "name": "ERP Support",
        "email": "support@erp.internal",
    },
    license_info={
        "name": "Proprietary",
    },
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(InputSanitizerMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


_NO_TIMEOUT_PATHS = {"/live", "/ready", "/health", "/metrics"}


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t0 = time.monotonic()
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
    request.state.request_id = request_id

    timeout = (
        None
        if request.url.path in _NO_TIMEOUT_PATHS
        else settings.REQUEST_TIMEOUT_SECONDS
    )

    try:
        if timeout:
            response = await asyncio.wait_for(call_next(request), timeout=timeout)
        else:
            response = await call_next(request)
    except asyncio.TimeoutError:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        record_request(request.method, request.url.path, 504, elapsed_ms)
        logger.warning(
            "Request timed out",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "timeout_seconds": timeout,
                "duration_ms": elapsed_ms,
            },
        )
        return JSONResponse(
            status_code=504,
            content={
                "error": "request_timeout",
                "detail": f"Request exceeded the {timeout}s timeout limit.",
                "path": request.url.path,
            },
            headers={REQUEST_ID_HEADER: request_id},
        )
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        record_request(request.method, request.url.path, 500, elapsed_ms)
        capture_exception(
            exc,
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": elapsed_ms,
            },
        )
        logger.exception(
            "Unhandled exception in request pipeline",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": elapsed_ms,
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": "An unexpected error occurred.",
                "path": request.url.path,
            },
            headers={REQUEST_ID_HEADER: request_id},
        )
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    response.headers[PROCESS_TIME_HEADER] = str(elapsed_ms)
    response.headers[REQUEST_ID_HEADER] = request_id
    record_request(request.method, request.url.path, response.status_code, elapsed_ms)
    if elapsed_ms > 500:
        logger.warning(
            "Slow request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": elapsed_ms,
            },
        )
    return response


app.include_router(api_router, prefix=settings.API_V1_STR)
register_handlers(app)


_db_health_cache: dict = {"status": "unknown", "checked_at": 0.0}
_DB_HEALTH_TTL = 8.0  # seconds


async def _check_db_health() -> str:
    now = time.monotonic()
    if now - _db_health_cache["checked_at"] < _DB_HEALTH_TTL:
        return _db_health_cache["status"]
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        _db_health_cache["status"] = "connected"
    except Exception as exc:
        logger.warning("Health check: database unavailable - %s", exc)
        _db_health_cache["status"] = "unavailable"
    _db_health_cache["checked_at"] = time.monotonic()
    return _db_health_cache["status"]


@app.get("/live")
async def liveness():
    """Kubernetes liveness probe — no external dependencies checked."""
    return {"status": "ok"}


@app.get("/ready")
async def readiness():
    """Kubernetes readiness probe — checks DB (cached)."""
    db_status = await _check_db_health()
    code = 200 if db_status == "connected" else 503
    return JSONResponse({"status": "ok" if code == 200 else "degraded", "database": db_status}, status_code=code)


@app.get("/health")
async def health():
    """Legacy combined health endpoint with cached DB check."""
    db_status = await _check_db_health()
    return {"status": "ok", "database": db_status}


@app.get("/metrics")
async def metrics():
    return metrics_snapshot()


@app.get("/")
async def root():
    return {"message": f"{settings.PROJECT_NAME} API", "docs": "/docs"}
