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
