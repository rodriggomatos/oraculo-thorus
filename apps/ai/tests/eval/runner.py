"""Roda 1 caso de eval contra o agente Thor real e retorna EvalResult."""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_litellm import ChatLiteLLM
from langgraph.checkpoint.memory import InMemorySaver

from uuid import UUID

from oraculo_ai.agents.qa.agent import _DEFAULT_USER_CONTEXT, _render_system_prompt
from oraculo_ai.agents.qa.mcp_client import get_drive_tools
from oraculo_ai.agents.qa.schema import UserContext
from oraculo_ai.agents.qa.tools import (
    find_project_by_name,
    list_projects,
    make_register_definition,
    search_definitions,
)
from oraculo_ai.core.config import Settings, get_settings
from oraculo_ai.core.db import close_db, init_db
from oraculo_ai.ingestion.schema import SYSTEM_USER_ID

from tests.eval.assertions import evaluate_assertions
from tests.eval.schemas import EvalCase


@dataclass
class ToolCallRecord:
    name: str
    args: dict[str, Any]


@dataclass
class EvalResult:
    case_id: str
    description: str
    input: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    actual_response: str = ""
    actual_tools: list[ToolCallRecord] = field(default_factory=list)
    duration_seconds: float = 0.0


def _resolve_api_key(model: str, settings: Settings) -> str | None:
    if model.startswith("anthropic/"):
        return settings.anthropic_api_key
    if model.startswith("groq/"):
        return settings.groq_api_key
    if model.startswith("openai/"):
        return settings.openai_api_key
    return None


_agent_singleton: Any | None = None
_db_initialized: bool = False


_TEST_USER = UserContext(
    user_id=SYSTEM_USER_ID,
    email="system@thorus.com.br",
    name="Eval Test Runner",
    role="system",
)


async def get_or_build_agent() -> Any:
    global _agent_singleton, _db_initialized
    if _agent_singleton is not None:
        return _agent_singleton

    settings = get_settings()

    if not _db_initialized:
        try:
            await init_db(settings.database_url, pool_size=2)
            _db_initialized = True
        except RuntimeError as exc:
            if "already initialized" not in str(exc):
                raise
            _db_initialized = True

    llm = ChatLiteLLM(
        model=settings.llm_model_smart,
        temperature=0,
        api_key=_resolve_api_key(settings.llm_model_smart, settings),
    )

    drive_tools = await get_drive_tools()
    register_definition_bound = make_register_definition(_TEST_USER.user_id)

    _agent_singleton = create_agent(
        model=llm,
        tools=[
            search_definitions,
            list_projects,
            find_project_by_name,
            register_definition_bound,
            *drive_tools,
        ],
        system_prompt=_render_system_prompt(_TEST_USER),
        checkpointer=InMemorySaver(),
    )
    return _agent_singleton


async def shutdown_eval_resources() -> None:
    global _agent_singleton, _db_initialized
    if _db_initialized:
        try:
            await close_db()
        except Exception:
            pass
        _db_initialized = False
    _agent_singleton = None


def _extract_response_text(messages: list[Any]) -> str:
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        content = msg.content
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text") or block.get("content")
                    if text:
                        parts.append(str(text))
                elif isinstance(block, str):
                    parts.append(block)
            joined = "\n".join(parts).strip()
            if joined:
                return joined
    return ""


def _extract_tool_calls(messages: list[Any]) -> list[ToolCallRecord]:
    calls: list[ToolCallRecord] = []
    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        for tc in (getattr(msg, "tool_calls", None) or []):
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
            args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
            if not name:
                continue
            calls.append(ToolCallRecord(name=str(name), args=dict(args or {})))
    return calls


async def run_case(agent: Any, case: EvalCase) -> EvalResult:
    start = time.monotonic()
    thread_id = f"eval-{case.id}-{uuid.uuid4().hex[:8]}"

    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": case.input}]},
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception as exc:
        return EvalResult(
            case_id=case.id,
            description=case.description,
            input=case.input,
            passed=False,
            failures=[f"agent invocation failed: {type(exc).__name__}: {exc}"],
            duration_seconds=time.monotonic() - start,
        )

    messages = result.get("messages", [])
    response_text = _extract_response_text(messages)
    tool_calls = _extract_tool_calls(messages)

    failures = evaluate_assertions(case.expected, response_text, tool_calls)

    return EvalResult(
        case_id=case.id,
        description=case.description,
        input=case.input,
        passed=not failures,
        failures=failures,
        actual_response=response_text,
        actual_tools=tool_calls,
        duration_seconds=time.monotonic() - start,
    )
