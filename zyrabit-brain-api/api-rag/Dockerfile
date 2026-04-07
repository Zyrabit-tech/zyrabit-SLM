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

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# STAGE 2: Runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

RUN addgroup --system zyrabituser && adduser --system --group zyrabituser

# Copiamos paquetes pip
COPY --from=builder /root/.local /home/zyrabituser/.local

# Copiamos código
COPY ./app ./app
COPY ./app/static ./app/static

# Ajuste el PATH
ENV PATH=/home/zyrabituser/.local/bin:$PATH

RUN chown -R zyrabituser:zyrabituser /app /home/zyrabituser/.local

USER zyrabituser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]