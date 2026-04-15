import os
import glob
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def _run_migrations() -> None:
    """Apply any SQL migration files in app/db/migrations/ that haven't run yet."""
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    sql_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    if not sql_files:
        return
    async with engine.begin() as conn:
        # Tracking table so we never apply a migration twice
        await conn.execute(__import__("sqlalchemy").text(
            "CREATE TABLE IF NOT EXISTS _migrations "
            "(filename TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT NOW())"
        ))
        for path in sql_files:
            filename = os.path.basename(path)
            result = await conn.execute(
                __import__("sqlalchemy").text(
                    "SELECT 1 FROM _migrations WHERE filename = :f"
                ),
                {"f": filename},
            )
            if result.fetchone():
                continue
            with open(path) as f:
                sql = f.read().strip()
            if sql:
                await conn.execute(__import__("sqlalchemy").text(sql))
                logger.info("Applied migration: %s", filename)
            await conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO _migrations (filename) VALUES (:f)"
                ),
                {"f": filename},
            )

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _run_migrations()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
