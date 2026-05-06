FROM python:3.11-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/0.10.7/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /workspace

COPY apps/ai/pyproject.toml apps/ai/uv.lock apps/ai/README.md ./apps/ai/
COPY apps/api/pyproject.toml apps/api/uv.lock ./apps/api/

COPY apps/ai/ ./apps/ai/
COPY apps/api/ ./apps/api/

WORKDIR /workspace/apps/api
RUN uv sync --frozen --no-dev


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/workspace/apps/api/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /workspace appuser

WORKDIR /workspace

COPY --from=builder /workspace /workspace
RUN chown -R appuser:app /workspace

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn oraculo_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
