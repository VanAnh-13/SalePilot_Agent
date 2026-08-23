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
from app.api.products import router as products_router
from app.api.runs import router as runs_router
# catalog_repository (imported at module top): verified no import cycle —
# app.catalog.repository only imports config + stdlib.
from app.catalog import repository as catalog_repository
from app.config import get_settings
from app.db.session import init_db
from app.services.scheduler import scheduler_loop


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path("data").mkdir(parents=True, exist_ok=True)
    Path("data/trajectories").mkdir(parents=True, exist_ok=True)
    await init_db()
    # Warm the catalog cache (MongoDB primary, snapshot fallback) off the event loop.
    count = await asyncio.to_thread(catalog_repository.load)
    print(f"[catalog] loaded {count} products from {catalog_repository.source()}")
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
        title="SalePilot-R",
        description=(
            "Constraint-first, evidence-grounded Vietnamese retail decision-support "
            "research prototype"
        ),
        version="0.7.0",
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
    app.include_router(memory_router)
    app.include_router(mcp_router)
    app.include_router(runs_router)
    app.include_router(jobs_router)

    @app.get("/")
    async def ping():
        """Lightweight liveness probe — no DB/catalog access, trả lời tức thì."""
        return {"ping": "pong", "ok": True}

    @app.get("/health")
    async def health():
        catalog_identity = catalog_repository.catalog_identity()
        category_count = len(catalog_repository.category_counts())
        return {
            "ok": True,
            "ready": bool(catalog_identity.get("products") and catalog_identity.get("sha256")),
            "service": "salepilot",
            "profile": "research-prototype",
            "architecture": "constraint-first-hybrid-decision-support",
            "shop": settings.shop_name,
            "default_category": settings.shop_category,
            "catalog": {
                "source": catalog_identity.get("backend"),
                "products": catalog_identity.get("products"),
                "categories": category_count,
                "sha256": catalog_identity.get("sha256"),
            },
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
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
