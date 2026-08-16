from fastapi import APIRouter, Depends

from app.agent.memory.store import list_memories, load_profile
from app.api.auth import require_admin_token

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("")
@router.get("/")
async def memory_list(
    limit: int = 50,
    _auth: None = Depends(require_admin_token),
):
    return await list_memories(limit=limit)


@router.get("/{channel}/{external_id}")
async def memory_one(
    channel: str,
    external_id: str,
    _auth: None = Depends(require_admin_token),
):
    profile = await load_profile(channel, external_id)
    return {"channel": channel, "external_id": external_id, "profile": profile}
