from typing import AsyncGenerator
from urllib.parse import parse_qsl, urlencode

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from shared.infra.db.config import settings


def to_asyncpg_url(url: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix) :]
    base, _, query = url.partition("?")
    if not query:
        return url
    params = dict(parse_qsl(query, keep_blank_values=True))
    params.pop("channel_binding", None)
    sslmode = params.pop("sslmode", None)
    if sslmode and "ssl" not in params:
        params["ssl"] = sslmode
    return f"{base}?{urlencode(params)}" if params else base


DATABASE_URL = to_asyncpg_url(settings.DATABASE_URL)


def build_engine(url: str) -> AsyncEngine:
    if settings.ENV == "test":
        # asyncpg connections are bound to an event loop and each test has its own.
        return create_async_engine(
            url, echo=settings.SQL_ECHO, hide_parameters=True, poolclass=NullPool
        )
    return create_async_engine(
        url,
        echo=settings.SQL_ECHO,
        hide_parameters=True,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )


engine = build_engine(DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
