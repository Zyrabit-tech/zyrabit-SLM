# STAGE 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/setup-uv:latest /uv /uvx /bin/

COPY requirements.txt .
# Install dependencies using uv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache -r requirements.txt && \
    uv run python -m spacy download en_core_web_sm

# STAGE 2: Runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Hardening: Update system, cleanup and REMOVE pip to close attack vector
RUN apt-get update && apt-get upgrade -y && \
    apt-get purge -y --auto-remove python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Copiamos solo lo necesario del builder
COPY --from=builder /opt/venv /opt/venv

# Crear usuario no-root
RUN addgroup --system zyrabituser && adduser --system --group zyrabituser

# Copiamos código
COPY ./app ./app

RUN mkdir -p /app/document_source && \
    chown -R zyrabituser:zyrabituser /app

USER zyrabituser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]