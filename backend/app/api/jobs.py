from fastapi import APIRouter

from app.services.scheduler import list_jobs, process_due_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
@router.get("/")
async def jobs_list(limit: int = 50):
    return await list_jobs(limit=limit)


@router.post("/tick")
async def jobs_tick():
    """Manual scheduler tick (also runs in background)."""
    n = await process_due_jobs()
    return {"processed": n}
