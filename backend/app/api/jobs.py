from fastapi import APIRouter, Depends

from app.api.auth import require_admin_token
from app.services.scheduler import list_jobs, process_due_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
@router.get("/")
async def jobs_list(
    limit: int = 50,
    _auth: None = Depends(require_admin_token),
):
    return await list_jobs(limit=limit)


@router.post("/tick")
async def jobs_tick(
    _auth: None = Depends(require_admin_token),
):
    """Manual scheduler tick (also runs in background)."""
    n = await process_due_jobs()
    return {"processed": n}
