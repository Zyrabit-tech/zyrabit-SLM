# syntax=docker/dockerfile:1.7
FROM --platform=linux/amd64 ubuntu:24.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ZYRABIT_TT_MODE=mock \
    ZYRABIT_TT_PORT=8090

# Instalamos Ubuntu 24.04 base para garantizar libstdc++6 >= 12.3.0
# Y usamos el PPA deadsnakes para tener Python 3.11 nativo (requerido por tt-forge cp311)
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    ca-certificates \
    curl \
    sudo \
    git \
    wget \
    pciutils \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalamos pip específico para Python 3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Seteamos Python 3.11 como el default del sistema
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /app

RUN addgroup --system zyrabit && adduser --system --ingroup zyrabit zyrabit

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

ARG INSTALL_TENSTORRENT=false
ARG TENSTORRENT_PYPI_URL=https://pypi.eng.aws.tenstorrent.com/
COPY requirements-tenstorrent.txt requirements-tenstorrent.txt

# Instalamos tt-forge y ejecutamos su instalador de sistema (que usa sudo)
# Al estar en Ubuntu 24.04 ya no fallará la dependencia de libstdc++6
RUN if [ "$INSTALL_TENSTORRENT" = "true" ]; then \
      pip install --extra-index-url "$TENSTORRENT_PYPI_URL" -r requirements-tenstorrent.txt && \
      tt-forge-install ; \
    fi

COPY zyrabit_tt_bridge.py zyrabit_tt_bridge.py

RUN chown -R zyrabit:zyrabit /app
USER zyrabit

EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://localhost:8090/v1/health >/dev/null || exit 1

CMD ["python", "zyrabit_tt_bridge.py", "serve"]
