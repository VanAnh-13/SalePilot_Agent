"""Request-scoped context for tools (conversation / channel)."""

from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class ToolContext:
    channel: str = "web"
    external_id: str = ""
    conversation_id: int | None = None
    lead_id: int | None = None
    customer_name: str = "Khách"
    used_tools: list[str] = field(default_factory=list)
    needs_human: bool = False


tool_context: ContextVar[ToolContext] = ContextVar("tool_context", default=ToolContext())


def get_ctx() -> ToolContext:
    return tool_context.get()


def set_ctx(ctx: ToolContext) -> None:
    tool_context.set(ctx)


def note_tool(name: str) -> None:
    ctx = get_ctx()
    ctx.used_tools.append(name)
