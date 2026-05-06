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

WORKDIR /workspace/apps/mcp-drive

COPY apps/mcp-drive/pyproject.toml apps/mcp-drive/uv.lock apps/mcp-drive/README.md ./
COPY apps/mcp-drive/ ./

RUN uv sync --frozen --no-dev


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/workspace/apps/mcp-drive/.venv/bin:$PATH" \
    MCP_DRIVE_TRANSPORT=streamable-http \
    MCP_DRIVE_HOST=0.0.0.0 \
    MCP_DRIVE_PORT=8001

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /workspace appuser

WORKDIR /workspace/apps/mcp-drive

COPY --from=builder /workspace/apps/mcp-drive /workspace/apps/mcp-drive
RUN chown -R appuser:app /workspace

USER appuser

EXPOSE 8001

CMD ["python", "-m", "mcp_drive"]
