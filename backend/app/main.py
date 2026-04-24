import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router
from app.config import settings
from app.db.database import init_db

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    async def reminder_loop():
        from app.services.reminder_service import run_reminder_check
        while True:
            try:
                await run_reminder_check()
            except Exception as exc:
                logger.error("Reminder loop error: %s", exc)
            await asyncio.sleep(6 * 3600)

    task = asyncio.create_task(reminder_loop())
    yield
    task.cancel()

app = FastAPI(
    title="Vendoroo Ops Diagnostic API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
