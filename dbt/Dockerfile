FROM debian:bookworm-slim

WORKDIR /app

# Certificats requis par uv pour les téléchargements HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# On épingle la version d'uv pour des builds reproductibles
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

# Configuration uv
ENV UV_NO_DEV=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_DOWNLOADS=auto
ENV UV_LINK_MODE=copy
ENV DBT_PROFILES_DIR=/app

# Utilisateur non-root
RUN groupadd --system app && useradd --system --gid app --no-create-home app

# Deps seules d'abord : ne casse le cache que si pyproject/lock changent
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Puis le code
COPY . .
RUN uv sync --frozen --no-dev

# On donne la main à l'utilisateur non-root sur /app
RUN chown -R app:app /app
USER app

# On lance main.py via uv
CMD ["uv", "run", "dbt", "run"]