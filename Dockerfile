# STAGE 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# STAGE 2: Runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

# Ensure base debian is up to date for CVEs like systemd/tar
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8501

RUN useradd -m zyrabituser && chown -R zyrabituser:zyrabituser /app
USER zyrabituser

ENTRYPOINT ["streamlit", "run", "slm_console.py", "--server.address=0.0.0.0"]
