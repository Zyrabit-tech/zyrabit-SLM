# STAGE 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock ./
# 1. Sync dependencies (this creates /app/.venv by default)
RUN uv sync --no-dev --no-install-project

# 2. Download spacy
RUN uv run python -m spacy download en_core_web_sm

# STAGE 2: Runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Hardening: Update system, cleanup and REMOVE pip
RUN apt-get update && apt-get upgrade -y && \
    apt-get purge -y --auto-remove python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Copiamos el entorno virtual estándar
COPY --from=builder /app/.venv /app/.venv

# Crear usuario no-root
RUN addgroup --system zyrabituser && adduser --system --group zyrabituser

# Copiamos solo la carpeta app (Ruta desde la raíz del proyecto)
COPY zyrabit-slm/api-rag/app ./app

RUN mkdir -p /app/document_source && \
    chown -R zyrabituser:zyrabituser /app

USER zyrabituser
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]