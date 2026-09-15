# ──────────────────────────────────────────────────────────────────────────────
#   ZYRABIT API-RAG — Multi-Stage Dockerfile (Production Stable)
#   Zero-Trust: Safe CI-compatible multi-core build, non-root user isolation.
# ──────────────────────────────────────────────────────────────────────────────

# STAGE 1: Builder ─────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    # Safe parallel C++ compilation (2 threads safe limit for GitHub Actions runners)
    CMAKE_BUILD_PARALLEL_LEVEL=2 \
    MAKEFLAGS="-j2"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl

ENV CFLAGS="-Wno-stringop-overflow -Wno-array-bounds -O2"
ENV CXXFLAGS="-Wno-stringop-overflow -Wno-array-bounds -O2"
ENV CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DCMAKE_C_FLAGS='-Wno-stringop-overflow' -DCMAKE_CXX_FLAGS='-Wno-stringop-overflow'"

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

ENV VIRTUAL_ENV=/app/.venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

RUN mkdir -p /app/document_source && touch /app/document_source/.keep


# STAGE 2: Runtime (Hardened Slim Python) ──────────────────────────────────────
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN groupadd -g 10001 nonroot && \
    useradd -m -d /home/nonroot -r -u 10001 -g nonroot nonroot && \
    mkdir -p /app/db_data && \
    chown -R nonroot:nonroot /app /home/nonroot

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libcurl4 \
    curl \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-spa

COPY --chown=nonroot:nonroot --from=builder /app/.venv /app/.venv
COPY --chown=nonroot:nonroot zyrabit-slm/api-rag/app ./app
COPY --chown=nonroot:nonroot --from=builder /app/document_source /app/document_source

ENV PYTHONPATH="/app/.venv/lib/python3.12/site-packages:/app" \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER nonroot

EXPOSE 8080

ENTRYPOINT ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
