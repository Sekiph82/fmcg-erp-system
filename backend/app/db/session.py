from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": False,
    "future": True,
}

if not _is_sqlite:
    _engine_kwargs.update(
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_recycle=settings.DATABASE_POOL_RECYCLE_SECONDS,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT_SECONDS,
        pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
    )

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
