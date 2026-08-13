FROM python:3.13-slim

WORKDIR /app

# Certificats requis par uv pour les téléchargements HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv épinglé pour des builds reproductibles
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

ENV UV_NO_DEV=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_DOWNLOADS=auto
ENV UV_LINK_MODE=copy
# Logs structurés en conteneur
ENV JSON_LOGS=true

RUN groupadd --system app && useradd --system --gid app --no-create-home app

# Deps seules d'abord (cache cassé seulement si pyproject/lock changent)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

# Puis le code
COPY src ./src
RUN uv sync --frozen --no-dev

# Les entrypoints déclarés dans [project.scripts] sont installés dans le venv.
# On les met sur le PATH pour qu'ils soient appelables par nom.
ENV PATH="/app/.venv/bin:$PATH"

RUN chown -R app:app /app
USER app

# pas de CMD : la commande est instruite dans le DAG Airflowr
# (cmds=["ingest-velib"] ou cmds=["ingest-meteo"] dans le KubernetesPodOperator)