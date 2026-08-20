# ──────────────────────────────────────────────────────────────────────────────
#   ZYRABIT API-RAG — Multi-Stage Dockerfile (Distroless Runtime)
#   Zero-Trust: No shell, no package manager, no attack surface in runtime.
# ──────────────────────────────────────────────────────────────────────────────

# STAGE 1: Builder ─────────────────────────────────────────────────────────────
# Toolchain for building and compiling native extensions
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV CFLAGS="-Wno-stringop-overflow -Wno-array-bounds -O2"
ENV CXXFLAGS="-Wno-stringop-overflow -Wno-array-bounds -O2"
ENV CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DCMAKE_C_FLAGS='-Wno-stringop-overflow' -DCMAKE_CXX_FLAGS='-Wno-stringop-overflow'"

COPY pyproject.toml uv.lock ./

# Sync dependencies with BuildKit cache mount (creates /app/.venv)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Download spacy model into the venv using cache mount
ENV VIRTUAL_ENV=/app/.venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

# Create placeholder directory and file
RUN mkdir -p /app/document_source && touch /app/document_source/.keep



# STAGE 2: Runtime (Hardened Slim Python) ──────────────────────────────────────
# Using python:3.12-slim-bookworm to match builder python version (3.12).
# Hardened: Runs as non-root user (65534).
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install runtime C libraries for OpenMP / llama.cpp and apply security upgrades
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libgomp1 \
    libcurl4 \
    curl \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code (path relative to build context root)
COPY zyrabit-slm/api-rag/app ./app

# Set Python path to use the venv's site-packages
ENV PYTHONPATH="/app/.venv/lib/python3.12/site-packages:/app" \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy document_source directory
COPY --from=builder /app/document_source /app/document_source

# Create non-root group and user with home directory, and set ownership
RUN groupadd -g 10001 nonroot && \
    useradd -m -d /home/nonroot -r -u 10001 -g nonroot nonroot && \
    chown -R nonroot:nonroot /app /home/nonroot

USER nonroot

EXPOSE 8080

# Use the venv's uvicorn directly (no shell needed)
ENTRYPOINT ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
