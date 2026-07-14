"""FastAPI entrypoint for the AI-First CRM – HCP Log Interaction module."""
from langchain_core.messages import AIMessage, HumanMessage
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graph import AGENT
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Interaction
from app.schemas import ChatRequest, ChatResponse, EMPTY_FORM, InteractionOut

app = FastAPI(title="AI-First CRM – HCP Module", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/")
def root() -> dict:
    return {
        "message": "AI-First CRM – HCP Module API",
        "docs": "/docs",
        "frontend": "http://localhost:5173",
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Single turn of the AI Assistant. The LangGraph agent decides which tool to
    call, mutates the form, and returns the auto-filled form + a reply."""
    config = {"configurable": {"thread_id": req.session_id}}
    inputs = {
        "messages": [HumanMessage(content=req.message)],
        # Frontend Redux store is the source of truth for the current form.
        "form_data": req.form_data or dict(EMPTY_FORM),
    }
    result = AGENT.invoke(inputs, config=config)

    # Collect the tools that fired on THIS turn (scan back to our human message).
    tools_used: list[str] = []
    for msg in reversed(result["messages"]):
        if isinstance(msg, HumanMessage):
            break
        if isinstance(msg, AIMessage) and msg.tool_calls:
            tools_used = [tc["name"] for tc in msg.tool_calls] + tools_used

    # Final assistant reply = last AI message without tool calls.
    reply = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            reply = msg.content
            break

    return ChatResponse(
        reply=reply or "Done.",
        form_data=result.get("form_data") or dict(EMPTY_FORM),
        tools_used=tools_used,
    )


@app.get("/api/interactions", response_model=list[InteractionOut])
def list_interactions() -> list[Interaction]:
    """Recent interactions (used by the demo / debugging)."""
    db = SessionLocal()
    try:
        return db.query(Interaction).order_by(Interaction.updated_at.desc()).limit(20).all()
    finally:
        db.close()
