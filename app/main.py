import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.billing.router import router as billing_router
from app.config import get_settings
from app.db import init_db
from app.instances.router import router as instances_router
from app.instances.scheduler import run_scheduler_forever
from app.marketplace.router import router as marketplace_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler_task = asyncio.create_task(run_scheduler_forever())
    yield
    scheduler_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await scheduler_task


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.include_router(auth_router)
    app.include_router(marketplace_router)
    app.include_router(billing_router)
    app.include_router(instances_router)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
