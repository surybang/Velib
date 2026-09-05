FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

ENV UV_NO_DEV=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_DOWNLOADS=never
ENV UV_LINK_MODE=copy
ENV DBT_PROFILES_DIR=/app
ENV PATH="/app/.venv/bin:$PATH"

RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev
RUN dbt deps --project-dir /app

RUN chown -R app:app /app
USER app
