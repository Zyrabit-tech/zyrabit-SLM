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

Prepare images and models on an online machine:

1. **Pull Images**:
```bash
docker pull zyrabitcore/zyrabit-slm:latest
docker pull ollama/ollama:latest
docker pull chromadb/chroma:latest
# ... (see zyrabit-brain-api/docker-compose.yml for full list)
```

2. **Save Images**:
```bash
docker save -o zyrabit-images.tar zyrabitcore/zyrabit-slm ollama/ollama chromadb/chroma
```

3. **Pre-populate Models**:
Download the model blobs to a local directory:
```bash
# On online machine
docker run -v $(pwd)/models:/root/.ollama ollama/ollama pull llama3
```

Transfer `zyrabit-images.tar` and the `models` folder to your offline server.

4. **Load and Run Offline**:
```bash
docker load -i zyrabit-images.tar
# Map the pre-populated models volume in your docker run or compose
docker run -d -v /path/to/models:/root/.ollama --name slm-engine ollama/ollama:latest
./zyra-up.sh start
```

> [!IMPORTANT]
> Ensure the model blobs are correctly placed in the mapped volume to prevent the engine from attempting an internet connection.

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
