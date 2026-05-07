from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

_db_url = (
    settings.DATABASE_URL
    .replace("postgresql://", "postgresql+asyncpg://")
    .split("?")[0]
)

# NullPool нужен для Supabase pooler (transaction mode)
engine = create_async_engine(
    _db_url,
    echo=False,
    poolclass=NullPool,
    connect_args={"ssl": "require"},
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
