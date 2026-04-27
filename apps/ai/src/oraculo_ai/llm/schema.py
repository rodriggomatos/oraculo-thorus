"""Schemas Pydantic do wrapper de LLM."""

from typing import Literal

from pydantic import BaseModel


ModelTier = Literal["fast", "smart"]


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatResponse(BaseModel):
    content: str
    model: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
