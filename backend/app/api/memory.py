from fastapi import APIRouter, Depends, HTTPException

from app.agent.memory.store import erase_memory, list_memories, load_profile
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


@router.delete("/{channel}/{external_id}")
async def memory_erase(
    channel: str,
    external_id: str,
    _auth: None = Depends(require_admin_token),
):
    """Erase one customer's stored memory (privacy / right to erasure)."""
    erased = await erase_memory(channel, external_id)
    if not erased:
        raise HTTPException(status_code=404, detail="No stored memory for this customer")
    return {"ok": True, "channel": channel, "external_id": external_id}
