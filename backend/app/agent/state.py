from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    channel: str
    external_id: str
    conversation_id: int | None
    lead_id: int | None
    customer_name: str
    needs_human: bool
    plan: str
    active_agents: list[str]
    subagent_results: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    final_reply: str
