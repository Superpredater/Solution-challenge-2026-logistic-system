"""SQLAlchemy 2 async engine setup with Row-Level Security helper."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from .config import settings


engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def set_rls_tenant(session: AsyncSession, tenant_id: UUID) -> None:
    """Set the PostgreSQL session variable for RLS tenant isolation."""
    await session.execute(text(f"SET app.tenant_id = '{tenant_id}'"))


@asynccontextmanager
async def get_db_session(tenant_id: UUID | None = None) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields a session with optional RLS tenant set."""
    async with AsyncSessionLocal() as session:
        if tenant_id is not None:
            await set_rls_tenant(session, tenant_id)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db(tenant_id: UUID | None = None) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with get_db_session(tenant_id) as session:
        yield session
