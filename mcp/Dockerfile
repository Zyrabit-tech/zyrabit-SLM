# STAGE 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY requirements.txt .
# Install dependencies using uv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache -r requirements.txt

# STAGE 2: Runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Hardening: Update system, cleanup and REMOVE pip
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends docker.io && \
    apt-get purge -y --auto-remove python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Copiamos el virtual environment
COPY --from=builder /opt/venv /opt/venv

COPY install_server.py .

EXPOSE 8001

# Crear usuario, agregarlo al grupo docker si existe para acceder al socket
RUN groupadd -g 999 docker || true && \
    useradd -m -o -u 1000 -g 999 zyrabituser || useradd -m zyrabituser && \
    chown -R zyrabituser /app

USER zyrabituser

CMD ["python", "install_server.py", "--http"]
