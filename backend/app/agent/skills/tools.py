import json

from langchain_core.tools import tool

from app.agent.run_bag import get_run_bag
from app.agent.skills.loader import list_skills, load_skill_body
from app.agent.tools.runtime import note_tool


@tool
async def list_skills_tool() -> str:
    """Liệt kê skills (metadata) có sẵn cho Lead."""
    note_tool("list_skills")
    items = [
        {"name": s.name, "description": s.description, "agents": s.agents}
        for s in list_skills()
    ]
    return json.dumps({"skills": items}, ensure_ascii=False)


@tool
async def activate_skill(name: str) -> str:
    """Nạp full body SKILL.md vào context lượt hiện tại (progressive skill load)."""
    note_tool("activate_skill")
    body = load_skill_body(name.strip())
    if not body:
        return json.dumps(
            {"ok": False, "error": f"Skill '{name}' không tồn tại", "available": [s.name for s in list_skills()]},
            ensure_ascii=False,
        )
    bag = get_run_bag()
    active = bag.setdefault("active_skills", [])
    if name not in active:
        active.append(name)
    bag.setdefault("skill_bodies", {})[name] = body[:4000]
    bag["trace"].append({"agent": "lead", "event": "skill", "detail": f"activate:{name}"})
    return json.dumps(
        {"ok": True, "name": name, "body_preview": body[:500], "chars": len(body)},
        ensure_ascii=False,
    )
