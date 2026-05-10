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
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.base import Base
from app.db.seed import seed_admin
from app.db.session import AsyncSessionLocal, engine
import app.models  # noqa: F401 - ensure all models are registered

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.PROJECT_NAME, settings.VERSION)
    if settings.ENVIRONMENT == "development" and settings.AUTO_CREATE_TABLES:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables verified/created successfully")
        except Exception:
            logger.exception("Database table creation failed; server will start but DB may be unavailable")
    else:
        logger.info("Automatic table creation disabled; use Alembic migrations for schema changes")

    try:
        async with AsyncSessionLocal() as db:
            await seed_admin(db)
        logger.info("Seed completed")
    except Exception:
        logger.exception("Seed failed; admin user may not exist yet")

    yield

    logger.info("Shutting down %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
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
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t0 = time.monotonic()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.exception(
            "Unhandled exception in request pipeline %s %s request_id=%s (%dms)",
            request.method,
            request.url.path,
            request_id,
            elapsed_ms,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": "An unexpected error occurred.",
                "path": request.url.path,
            },
            headers={"X-Request-ID": request_id},
        )
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    response.headers["X-Request-ID"] = request_id
    if elapsed_ms > 500:
        logger.warning("SLOW %s %s request_id=%s -> %dms", request.method, request.url.path, request_id, elapsed_ms)
    return response


app.include_router(api_router, prefix=settings.API_V1_STR)
register_handlers(app)


@app.get("/health")
async def health():
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.warning("Health check: database unavailable - %s", e)
        db_status = "unavailable"
    return {"status": "ok", "database": db_status}


@app.get("/")
async def root():
    return {"message": f"{settings.PROJECT_NAME} API", "docs": "/docs"}
