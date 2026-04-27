"""Wrapper LiteLLM — único ponto de acesso a LLMs e embeddings."""

import os
import time

from oraculo_ai.core.config import get_settings
from oraculo_ai.llm.schema import ChatResponse, Message, ModelTier


_settings = get_settings()

if _settings.langfuse_public_key:
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", _settings.langfuse_public_key)
if _settings.langfuse_secret_key:
    os.environ.setdefault("LANGFUSE_SECRET_KEY", _settings.langfuse_secret_key)
if _settings.langfuse_host:
    os.environ.setdefault("LANGFUSE_HOST", _settings.langfuse_host)
if _settings.groq_api_key:
    os.environ.setdefault("GROQ_API_KEY", _settings.groq_api_key)
if _settings.openai_api_key:
    os.environ.setdefault("OPENAI_API_KEY", _settings.openai_api_key)

import litellm  # noqa: E402
from langfuse import get_client, observe  # noqa: E402


def _resolve_model(tier: ModelTier) -> str:
    if tier == "fast":
        return _settings.llm_model_fast
    return _settings.llm_model_smart


@observe(as_type="generation", name="llm-complete")
async def complete(messages: list[Message], model: ModelTier = "fast") -> ChatResponse:
    resolved_model = _resolve_model(model)
    payload = [m.model_dump() for m in messages]

    start = time.perf_counter()
    response = await litellm.acompletion(
        model=resolved_model,
        messages=payload,
        num_retries=3,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)

    content = response.choices[0].message.content
    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens

    get_client().update_current_generation(
        input=payload,
        output=content,
        model=response.model,
        usage_details={"input": prompt_tokens, "output": completion_tokens},
    )

    return ChatResponse(
        content=content,
        model=response.model,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


@observe(as_type="generation", name="llm-embed")
async def embed(texts: list[str]) -> list[list[float]]:
    response = await litellm.aembedding(
        model=_settings.embedding_model,
        input=texts,
    )
    vectors = [item["embedding"] for item in response.data]

    update_kwargs: dict[str, object] = {
        "input": texts,
        "model": _settings.embedding_model,
        "output": {"count": len(vectors), "dim": len(vectors[0]) if vectors else 0},
    }
    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None) if usage is not None else None
    if prompt_tokens is not None:
        update_kwargs["usage_details"] = {"input": prompt_tokens}
    get_client().update_current_generation(**update_kwargs)

    return vectors


def shutdown_traces() -> None:
    try:
        get_client().shutdown()
    except Exception:
        pass
