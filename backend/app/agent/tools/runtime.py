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


tool_context: ContextVar[ToolContext] = ContextVar("tool_context")


def get_ctx() -> ToolContext:
    try:
        return tool_context.get()
    except LookupError:
        return ToolContext()


def set_ctx(ctx: ToolContext) -> None:
    tool_context.set(ctx)


def prepare_ctx(
    *,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    lead_id: int | None,
    customer_name: str,
) -> ToolContext:
    """Build and install the request-scoped context for this turn."""
    ctx = ToolContext(
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
    )
    set_ctx(ctx)
    return ctx


def note_tool(name: str) -> None:
    ctx = get_ctx()
    ctx.used_tools.append(name)
