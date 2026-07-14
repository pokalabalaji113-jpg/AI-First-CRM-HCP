"""Pydantic request/response schemas for the API."""
from typing import Any, Optional

from pydantic import BaseModel, Field


# The canonical, empty form used by the frontend Redux store.
EMPTY_FORM: dict[str, Any] = {
    "id": None,
    "hcp_name": "",
    "interaction_type": "",
    "date": "",
    "time": "",
    "attendees": "",
    "topics_discussed": "",
    "materials_shared": "",
    "samples_distributed": "",
    "sentiment": "",
    "outcomes": "",
    "follow_up_actions": "",
    "ai_suggested_followups": [],
}


class ChatRequest(BaseModel):
    """A single user turn from the AI Assistant panel."""
    session_id: str = Field(..., description="Stable id per browser tab; used as LangGraph thread_id.")
    message: str
    form_data: dict[str, Any] = Field(default_factory=lambda: dict(EMPTY_FORM))


class ChatResponse(BaseModel):
    reply: str                       # assistant's natural-language reply
    form_data: dict[str, Any]        # the (auto-filled) form to render in the UI
    tools_used: list[str] = []       # which LangGraph tools fired this turn


class InteractionOut(BaseModel):
    id: int
    hcp_name: str
    interaction_type: str
    date: str
    time: str
    topics_discussed: str
    sentiment: str

    class Config:
        from_attributes = True
