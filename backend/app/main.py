import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.jobs import router as jobs_router
from app.api.leads import router as leads_router
from app.api.memory import router as memory_router
from app.api.mcp import router as mcp_router
from app.api.outbox import router as outbox_router
from app.api.products import router as products_router
from app.api.runs import router as runs_router
from app.channels.zalo.webhook import router as zalo_router
from app.config import get_settings
from app.db.session import init_db
from app.services.scheduler import scheduler_loop


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path("data").mkdir(parents=True, exist_ok=True)
    Path("data/trajectories").mkdir(parents=True, exist_ok=True)
    await init_db()
    stop = asyncio.Event()
    task = asyncio.create_task(scheduler_loop(stop))
    yield
    stop.set()
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except (asyncio.TimeoutError, Exception):
        task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SalePilot",
        description="AI so sánh & tư vấn tủ lạnh theo nhu cầu — VAIC Điện Máy Xanh / SME",
        version="0.6.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(chat_router)
    app.include_router(leads_router)
    app.include_router(products_router)
    app.include_router(outbox_router)
    app.include_router(zalo_router)
    app.include_router(memory_router)
    app.include_router(mcp_router)
    app.include_router(runs_router)
    app.include_router(jobs_router)

    @app.get("/health")
    async def health():
        return {
            "ok": True,
            "service": "salepilot",
            "architecture": "product-advisor-multi-agent",
            "shop": settings.shop_name,
            "category": settings.shop_category,
            "llm_provider": settings.llm_provider,
            "features": {
                "memory": settings.memory_enabled,
                "sandbox": settings.sandbox_enabled,
                "web_fetch": settings.web_fetch_enabled,
                "scheduler": settings.scheduler_enabled,
                "trajectory": settings.trajectory_enabled,
                "auto_skill_write": settings.auto_skill_write,
            },
        }

    return app


app = create_app()
