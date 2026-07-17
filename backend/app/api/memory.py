from fastapi import APIRouter

from app.agent.memory.store import list_memories, load_profile

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("")
@router.get("/")
async def memory_list(limit: int = 50):
    return await list_memories(limit=limit)


@router.get("/{channel}/{external_id}")
async def memory_one(channel: str, external_id: str):
    profile = await load_profile(channel, external_id)
    return {"channel": channel, "external_id": external_id, "profile": profile}
