# One image for the api, worker, scheduler, and console. Dependencies come from uv.lock only.
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so code changes do not reinstall them.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project

COPY platform ./platform
RUN uv sync --frozen --no-dev

# uid 1000 matches the usual host user, so the shared spend ledger stays writable on both sides.
RUN useradd --create-home --uid 1000 datapilot
USER datapilot
