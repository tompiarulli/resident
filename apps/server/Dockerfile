# Build from the repo root: docker build -f apps/server/Dockerfile .
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY apps/server ./apps/server
RUN uv sync --frozen --no-dev --package resident-server

ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app/apps/server
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn resident_server.main:asgi --host 0.0.0.0 --port 8000"]
