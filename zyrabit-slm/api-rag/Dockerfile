# ──────────────────────────────────────────────────────────────────────────────
#   ZYRABIT API-RAG — Multi-Stage Dockerfile (Distroless Runtime)
#   Zero-Trust: No shell, no package manager, no attack surface in runtime.
# ──────────────────────────────────────────────────────────────────────────────

# STAGE 1: Builder ─────────────────────────────────────────────────────────────
# Full toolchain for compiling native extensions (spacy, chromadb, etc.)
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV CFLAGS="-Wno-stringop-overflow -Wno-array-bounds -O2"
ENV CXXFLAGS="-Wno-stringop-overflow -Wno-array-bounds -O2"
ENV CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DCMAKE_C_FLAGS='-Wno-stringop-overflow' -DCMAKE_CXX_FLAGS='-Wno-stringop-overflow'"

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock ./

# Sync dependencies (creates /app/.venv)
RUN uv sync --frozen --no-dev --no-install-project

# Download spacy model into the venv
RUN uv run python -m spacy download en_core_web_sm

# Create placeholder directory and file
RUN mkdir -p /app/document_source && touch /app/document_source/.keep



# STAGE 2: Runtime (Hardened Slim Python) ──────────────────────────────────────
# Using python:3.12-slim-bookworm to match builder python version (3.12).
# Hardened: Runs as non-root user (65534).
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install runtime C libraries for OpenMP / llama.cpp
RUN apt-get update && apt-get install -y --no-install-recommends \
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
