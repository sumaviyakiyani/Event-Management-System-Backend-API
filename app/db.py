"""Async database engine, session factory and helpers."""
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def to_async_url(url: str) -> str:
    """Make sure the URL uses the asyncpg driver (accepts plain postgresql://)."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# The engine does not connect until the first query, so importing is safe.
engine = create_async_engine(to_async_url(DATABASE_URL), pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields one database session per request."""
    async with AsyncSessionLocal() as session:
        yield session


async def check_connection() -> None:
    """Run SELECT 1; raises if PostgreSQL cannot be reached."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def init_models() -> None:
    """Create all tables that do not exist yet."""
    import app.models  # noqa: F401  (registers models on Base.metadata)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
