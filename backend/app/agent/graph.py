"""LangGraph agent that manages HCP interactions.

Role of the agent (assignment: "Describe the role of the LangGraph agent"):
  It is the single brain of the Log Interaction Screen. The field rep talks to it
  in plain language; the agent (powered by Groq) decides which tool to call, extracts
  the entities, and drives the form state — logging, editing, erasing, searching and
  suggesting follow-ups. No form logic is hardcoded: the LLM + graph make every call.
"""
import json
from typing import Annotated, TypedDict

from groq import BadRequestError
from langchain_core.messages import AIMessage, SystemMessage   # AIMessage added
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.llm import get_llm
from app.agent.tools import ALL_TOOLS, TEXT_FIELDS


def _merge_form(left: dict | None, right: dict | None) -> dict:
    """Reducer for form_data: merge updates instead of crashing when more than
    one tool writes in the same step (right-hand values win on overlap)."""
    return {**(left or {}), **(right or {})}


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    form_data: Annotated[dict, _merge_form]


SYSTEM_PROMPT = (
    "You are the AI Assistant inside an AI-first pharma CRM, on the 'Log HCP "
    "Interaction' screen. Field representatives log meetings with Healthcare "
    "Professionals (HCPs) by TALKING TO YOU — they never fill the form manually.\n\n"
    "Your job:\n"
    "- Read the rep's natural language and call the correct tool.\n"
    "- To record a NEW interaction (a new HCP or a new visit), call log_interaction "
    "and extract every detail (HCP name, type, topics, materials, samples, sentiment, "
    "outcomes, follow-ups). log_interaction ALWAYS creates a new record.\n"
    "- To add to or change a field on the interaction ALREADY on screen, call "
    "edit_interaction(field, value) — do NOT call log_interaction for that.\n"
    "- To remove/clear something, call delete_interaction(field) (field='all' wipes it).\n"
    "- To look up past interactions, call search_interactions.\n"
    "- When asked for next steps / follow-ups, call suggest_followups.\n"
    f"- Valid form fields: {', '.join(TEXT_FIELDS)}.\n"
    "- interaction_type ∈ {Meeting, Call, Email, Conference, Virtual}; "
    "sentiment ∈ {Positive, Neutral, Negative}.\n"
    "After a tool runs, reply to the rep in ONE short, friendly sentence confirming "
    "what you did. Never ask the rep to type into the form themselves."
)


def _agent_node(state: AgentState) -> dict:
    """Call the Groq LLM (with tools bound) to decide the next action."""
    llm_with_tools = get_llm(temperature=0).bind_tools(ALL_TOOLS, parallel_tool_calls=False)
    form_context = SystemMessage(
        content=SYSTEM_PROMPT
        + "\n\nCurrent form state (JSON):\n"
        + json.dumps(state.get("form_data") or {}, ensure_ascii=False)
    )
    try:
        response = llm_with_tools.invoke([form_context] + state["messages"])
    except BadRequestError as exc:
        # Groq's Llama models occasionally emit malformed tool-call markup
        # (e.g. '<function=delete_interaction{"field": "all"}</function>' — missing
        # the '>' after the name). Groq rejects it with code 'tool_use_failed'.
        if getattr(exc, "code", None) == "tool_use_failed":
            return {"messages": [AIMessage(
                content="Sorry, I couldn't complete that action just now — "
                "could you rephrase it? (e.g. \"clear the form\" or "
                "\"delete this interaction\")."
            )]}
        raise
    return {"messages": [response]}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    # In-memory checkpointer keeps per-session (thread_id) conversation + form state.
    return graph.compile(checkpointer=MemorySaver())


# Singleton compiled agent, imported by the FastAPI app.
AGENT = build_graph()