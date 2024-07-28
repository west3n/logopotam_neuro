from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from src.core.config import settings


BaseModel = declarative_base()
engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)


async def create_metadata() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as session:
        yield session
    await engine.dispose()
