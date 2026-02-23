# Installation

## Quick start

```bash
curl -sSL https://zyrabit.com/install.sh | bash
```

## Local setup

```bash
chmod +x zyra-up.sh
./zyra-up.sh install
```

The script detects NVIDIA, Apple Silicon, or CPU-only hosts and selects model defaults accordingly.

## Script responsibilities

- `install.sh`: bootstrap helper for first-time setup.
- `zyra-up.sh`: validates environment and orchestrates lifecycle (`doctor`, `start`, `install`).

## Manual docker workflow

```bash
cd zyrabit-brain-api
docker compose up -d
```

Enable optional profiles:

```bash
docker compose --profile docs up -d docs-portal
docker compose --profile automation up -d n8n
```

## Manual model pull

```bash
docker compose -f zyrabit-brain-api/docker-compose.yml up -d slm-engine
docker compose -f zyrabit-brain-api/docker-compose.yml exec -T slm-engine ollama pull qwen2.5:7b
docker compose -f zyrabit-brain-api/docker-compose.yml exec -T slm-engine ollama pull mxbai-embed-large
```

## Air-gapped workflow

Prepare images on an online machine:

```bash
docker pull traefik:latest
docker pull ollama/ollama:latest
docker pull chromadb/chroma:latest
docker pull prom/prometheus:latest
docker pull grafana/grafana:latest
docker pull n8nio/n8n:latest
docker save -o zyrabit-images.tar \
  traefik:latest ollama/ollama:latest chromadb/chroma:latest \
  prom/prometheus:latest grafana/grafana:latest n8nio/n8n:latest
```

Transfer `zyrabit-images.tar` by controlled media and load offline:

```bash
docker load -i zyrabit-images.tar
./zyra-up.sh start
```

## Single-entry observability access

- `https://localhost/grafana`
- `https://localhost/prometheus`

Use Traefik basic auth via:

```bash
PROMETHEUS_BASIC_AUTH=<user:htpasswd_hash>
GRAFANA_BASIC_AUTH=<user:htpasswd_hash>
```

Generate a bcrypt htpasswd hash:

```bash
htpasswd -nbB admin 'change-this'
```
