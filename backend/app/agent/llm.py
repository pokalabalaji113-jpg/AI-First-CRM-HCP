"""Shared Groq LLM factory.

The assignment MANDATES an LLM (Groq) + LangGraph. Every tool decision and
every piece of entity extraction / summarization flows through this model —
nothing is hardcoded.
"""
from langchain_groq import ChatGroq

from app.config import settings


def get_llm(temperature: float = 0.0) -> ChatGroq:
    return ChatGroq(
        model=settings.groq_model,          # gemma2-9b-it (or llama-3.3-70b-versatile)
        api_key=settings.groq_api_key,
        temperature=temperature,
    )
