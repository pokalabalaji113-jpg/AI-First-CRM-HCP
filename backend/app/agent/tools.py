"""The 5 LangGraph tools that drive the Log Interaction Screen.

IMPORTANT (assignment requirement):
  The user NEVER fills the form manually. The Groq LLM reads the user's natural
  language, decides which of these tools to call, and passes the extracted
  arguments. Each tool then mutates the shared `form_data` state (which the
  frontend renders) and persists to PostgreSQL. The form on screen is a live
  mirror of this agent-controlled state.

Tools:
  1. log_interaction     (MANDATORY) – extract entities from free text & fill/save the form
  2. edit_interaction    (MANDATORY) – modify one field of the logged interaction
  3. delete_interaction              – erase a single field or the whole interaction by prompt
  4. search_interactions             – look up previously logged interactions
  5. suggest_followups               – LLM generates AI follow-up suggestions
"""
from datetime import datetime
from typing import Annotated, Optional

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.agent.llm import get_llm
from app.database import SessionLocal
from app.models import Interaction

# Plain text fields that live on the form + DB row.
TEXT_FIELDS = [
    "hcp_name",
    "interaction_type",
    "date",
    "time",
    "attendees",
    "topics_discussed",
    "materials_shared",
    "samples_distributed",
    "sentiment",
    "outcomes",
    "follow_up_actions",
]

EMPTY_FORM = {
    "id": None,
    **{f: "" for f in TEXT_FIELDS},
    "ai_suggested_followups": [],
}


# --------------------------------------------------------------------------- #
# Persistence helpers                                                          #
# --------------------------------------------------------------------------- #
def _persist(form: dict) -> dict:
    """Create or update the interaction row from `form`; return the saved form."""
    db = SessionLocal()
    try:
        rec = db.get(Interaction, form["id"]) if form.get("id") else None
        if rec is None:
            rec = Interaction()
            db.add(rec)
        for f in TEXT_FIELDS:
            setattr(rec, f, (form.get(f) or ""))
        rec.ai_suggested_followups = "\n".join(form.get("ai_suggested_followups") or [])
        db.commit()
        db.refresh(rec)
        return rec.as_form()
    finally:
        db.close()


def _command(form: dict, tool_call_id: str, message: str) -> Command:
    """Standard tool return: push new form_data into state + a ToolMessage."""
    return Command(
        update={
            "form_data": form,
            "messages": [ToolMessage(content=message, tool_call_id=tool_call_id)],
        }
    )


def _current_form(state: dict) -> dict:
    form = dict(EMPTY_FORM)
    form.update(state.get("form_data") or {})
    return form


# --------------------------------------------------------------------------- #
# 1. LOG INTERACTION  (mandatory)                                             #
# --------------------------------------------------------------------------- #
@tool
def log_interaction(
    hcp_name: Optional[str] = None,
    interaction_type: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    attendees: Optional[str] = None,
    topics_discussed: Optional[str] = None,
    materials_shared: Optional[str] = None,
    samples_distributed: Optional[str] = None,
    sentiment: Optional[str] = None,
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None,
    *,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Log a new HCP interaction. Extract every detail the rep mentioned in natural
    language and pass it as the matching argument (leave unknown ones empty).

    - interaction_type: one of Meeting, Call, Email, Conference, Virtual.
    - sentiment: one of Positive, Neutral, Negative.
    - date: format DD-MM-YYYY. time: format HH:MM. If the rep didn't say, leave empty
      and the system will stamp the current date/time.

    NOTE: This ALWAYS starts a fresh, separate interaction record (new row). To
    add to or change the interaction already on screen, use edit_interaction.
    """
    # Start from a clean, empty form so each logged interaction is its own record
    # (id stays None -> a new row is INSERTed, never overwriting a previous one).
    form = dict(EMPTY_FORM)

    provided = {
        "hcp_name": hcp_name,
        "interaction_type": interaction_type,
        "date": date,
        "time": time,
        "attendees": attendees,
        "topics_discussed": topics_discussed,
        "materials_shared": materials_shared,
        "samples_distributed": samples_distributed,
        "sentiment": sentiment,
        "outcomes": outcomes,
        "follow_up_actions": follow_up_actions,
    }
    for key, value in provided.items():
        if value:
            form[key] = value

    # Sensible defaults so a logged interaction always has a timestamp.
    now = datetime.now()
    if not form.get("date"):
        form["date"] = now.strftime("%d-%m-%Y")
    if not form.get("time"):
        form["time"] = now.strftime("%H:%M")
    if not form.get("interaction_type"):
        form["interaction_type"] = "Meeting"

    saved = _persist(form)
    filled = [k for k, v in provided.items() if v]
    msg = (
        f"Logged interaction #{saved['id']} for "
        f"{saved.get('hcp_name') or 'the HCP'}. "
        f"Fields captured: {', '.join(filled) or 'defaults only'}."
    )
    return _command(saved, tool_call_id, msg)


# --------------------------------------------------------------------------- #
# 2. EDIT INTERACTION  (mandatory)                                           #
# --------------------------------------------------------------------------- #
@tool
def edit_interaction(
    field: str,
    value: str,
    *,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Edit ONE field of the currently loaded interaction.

    `field` must be one of: hcp_name, interaction_type, date, time, attendees,
    topics_discussed, materials_shared, samples_distributed, sentiment,
    outcomes, follow_up_actions. `value` is the new text to set.
    """
    form = _current_form(state)
    field = (field or "").strip().lower()
    if field not in TEXT_FIELDS:
        return _command(
            form,
            tool_call_id,
            f"Cannot edit '{field}'. Valid fields: {', '.join(TEXT_FIELDS)}.",
        )
    form[field] = value
    saved = _persist(form)
    return _command(saved, tool_call_id, f"Updated '{field}' to: {value!r}.")


# --------------------------------------------------------------------------- #
# 3. DELETE / ERASE INTERACTION                                              #
# --------------------------------------------------------------------------- #
@tool
def delete_interaction(
    field: str = "all",
    *,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Erase logged data by prompt (never manually).

    - field="all"  -> delete the whole interaction and clear the form.
    - field=<name> -> clear just that one field (e.g. 'samples_distributed').
    """
    form = _current_form(state)
    field = (field or "all").strip().lower()

    if field == "all":
        if form.get("id"):
            db = SessionLocal()
            try:
                rec = db.get(Interaction, form["id"])
                if rec:
                    db.delete(rec)
                    db.commit()
            finally:
                db.close()
        return _command(dict(EMPTY_FORM), tool_call_id, "Cleared the interaction. Form is now empty.")

    if field not in TEXT_FIELDS:
        return _command(form, tool_call_id, f"Cannot erase '{field}'. Valid fields: {', '.join(TEXT_FIELDS)}.")

    form[field] = ""
    saved = _persist(form)
    return _command(saved, tool_call_id, f"Erased the '{field}' field.")


# --------------------------------------------------------------------------- #
# 4. SEARCH INTERACTIONS                                                      #
# --------------------------------------------------------------------------- #
@tool
def search_interactions(
    hcp_name: str = "",
    *,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Search previously logged interactions, optionally filtered by HCP name.
    Returns a short summary list (does not change the current form)."""
    db = SessionLocal()
    try:
        query = db.query(Interaction)
        if hcp_name:
            query = query.filter(Interaction.hcp_name.ilike(f"%{hcp_name}%"))
        rows = query.order_by(Interaction.updated_at.desc()).limit(5).all()
    finally:
        db.close()

    if not rows:
        msg = "No matching interactions found."
    else:
        lines = [
            f"#{r.id} | {r.hcp_name or 'Unknown'} | {r.interaction_type or '-'} | "
            f"{r.date or '-'} | sentiment: {r.sentiment or '-'} | "
            f"topics: {(r.topics_discussed or '')[:60]}"
            for r in rows
        ]
        msg = "Found these interactions:\n" + "\n".join(lines)

    return Command(update={"messages": [ToolMessage(content=msg, tool_call_id=tool_call_id)]})


# --------------------------------------------------------------------------- #
# 5. SUGGEST FOLLOW-UPS  (LLM-generated)                                      #
# --------------------------------------------------------------------------- #
@tool
def suggest_followups(
    *,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Use the LLM to generate 2-4 concrete AI follow-up suggestions based on the
    current interaction, and populate the 'AI Suggested Follow-ups' section."""
    form = _current_form(state)

    context = "\n".join(f"{f}: {form.get(f)}" for f in TEXT_FIELDS if form.get(f))
    llm = get_llm(temperature=0.3)
    prompt = [
        SystemMessage(
            content=(
                "You are a pharma field-sales assistant. Given the logged HCP "
                "interaction, propose 2-4 short, concrete follow-up actions "
                "(e.g. 'Schedule follow-up meeting in 2 weeks', 'Send OncoBoost "
                "Phase III PDF'). Return ONLY the actions, one per line, no numbering."
            )
        ),
        HumanMessage(content=context or "No details captured yet."),
    ]
    result = llm.invoke(prompt)
    suggestions = [line.strip("-• ").strip() for line in result.content.splitlines() if line.strip()]
    suggestions = suggestions[:4]

    form["ai_suggested_followups"] = suggestions
    saved = _persist(form)
    msg = "Generated AI follow-up suggestions:\n" + "\n".join(f"- {s}" for s in suggestions)
    return _command(saved, tool_call_id, msg)


ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    delete_interaction,
    search_interactions,
    suggest_followups,
]