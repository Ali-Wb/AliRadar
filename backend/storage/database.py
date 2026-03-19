from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from backend.config import settings
from backend.storage.models import Base


ASYNC_DATABASE_URL = f"sqlite+aiosqlite:///{settings.DB_PATH}"
SYNC_DATABASE_URL = f"sqlite:///{settings.DB_PATH}"

async_engine = create_async_engine(ASYNC_DATABASE_URL, future=True)
sync_engine = create_engine(SYNC_DATABASE_URL, future=True)

AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


async def init_db() -> None:
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncSession:
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
