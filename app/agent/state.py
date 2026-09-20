"""LangGraph agent state schema."""

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """Conversational state for the LangGraph agent."""

    phone_number: str
    user_message: str
    intent: str | None
    options: dict[str, Any]
    response_message: str | None
    context: dict[str, Any]
