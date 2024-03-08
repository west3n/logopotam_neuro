import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, AsyncAttrs, async_sessionmaker
from sqlalchemy.orm import declarative_base

from src.core.config import settings


BaseModel = declarative_base()


async def get_session():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=True)
    return async_session


if __name__ == '__main__':
    asyncio.run(get_session())
