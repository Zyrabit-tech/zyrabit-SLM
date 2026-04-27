# Zyrabit SLM Secure Suite

[![Spanish](https://img.shields.io/badge/lang-Spanish-blue.svg)](README.md)
[![Python](https://img.shields.io/badge/python-3.12%20recommended-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker--compose-ready-green.svg)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Local AI suite with **SLM + RAG + Heuristic-based Data Scrubbing (PII Guard)**.

## What this project runs

- `traefik`: local HTTPS entrypoint (`https://localhost`)
- `api-rag`: main API (chat, ingest, mcp, webhooks)
- `slm-engine`: local inference with Ollama
- `vector-db`: ChromaDB knowledge store
- `prometheus` + `grafana`: metrics and dashboards
- `docs-portal` (optional)
- `n8n` (optional)

Docker networks:

- `frontend-network`
- `backend-network`
- `model-network` (`internal: true`)

## Ollama Installation (Native vs Docker)

By default, Zyrabit spins up Ollama inside Docker (`slm-engine`). However, to take full advantage of your hardware (GPU/Metal) on Mac or Windows, and to avoid performance or networking overhead, **we strongly recommend installing Ollama natively** (as an OS background process).

### 🍎 macOS
1. Download Ollama from [ollama.com/download/mac](https://ollama.com/download/mac).
2. Unzip and install the `Ollama.app` application.
3. Open the app; Ollama will run in the background (you'll see a menu bar icon).
4. The service will be available locally at `http://localhost:11434`.

### 🪟 Windows
1. Download the installer from [ollama.com/download/windows](https://ollama.com/download/windows).
2. Run `OllamaSetup.exe`.
3. Ollama will start automatically and sit in your system tray.
4. The service will be available locally at `http://localhost:11434`.

### 🐧 Ubuntu / Linux
You can stick to the default Docker option, or install it natively by running this command in your terminal:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### ⚙️ Configuring Zyrabit to use Native Ollama
If you choose the native route, tell Zyrabit where to find Ollama by editing the `zyrabit-slm/.env` file (copy from `example.env` if you haven't already):

- **Mac / Windows**:
  ```env
  INFERENCE_PROVIDER=ollama_host
  SLM_URL=http://host.docker.internal:11434/api/generate
  ```
- **Linux** (Use your docker bridge IP, e.g. `172.17.0.1` or `localhost` if running without Docker):
  ```env
  INFERENCE_PROVIDER=ollama_host
  SLM_URL=http://172.17.0.1:11434/api/generate
  ```

*(Optional) Once configured, you can stop/comment out the `slm-engine` service in your `docker-compose.yml` to save RAM.*

## Quick start (UI + API)

1. Prerequisites:

```bash
docker --version
docker compose version
python3 --version
```

2. Install local Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Start backend stack:

```bash
chmod +x zyra-up.sh
./zyra-up.sh doctor
./zyra-up.sh start
```


## Functional verification (end-to-end)

### 1) Backend health

```bash
curl -k https://localhost/health
```

Expected: `{"status":"ok", ...}`.

### 2) Normal chat

```bash
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"Explain the Zyrabit architecture"}'
```

You should see `metadata.route_decision`, `rag_hits`, and `latency_ms`.

### 3) Gatekeeper (out-of-policy rejection)

```bash
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"comprar viagra barato ahora"}'
```

Expected: `400` + `detail` (`reject_query` route).

### 4) Heuristic-based Data Scrubbing (PII Sanitization)

```bash
python secure_agent.py "My email is john@example.com and my account is 4532-1234-5678-9012"
```

The pipeline uses **heuristic-based pattern matching (Regex)** to anonymize entities (for example `<USER_EMAIL_1>`) before inference and restores them in the final response. 

> [!NOTE]
> This is a prevention layer for accidental data leaks, not a replacement for legal-grade auditing.

### 5) Token and security metrics

```bash
curl -k https://localhost/metrics | grep zyrabit_token_usage_total
curl -k https://localhost/metrics | grep zyrabit_token_latency_ms_per_token
curl -k https://localhost/metrics | grep zyrabit_security_hits_total
```

## How to open each local component

- API docs: `https://localhost/docs`
- Grafana: `https://localhost/grafana`
- Prometheus: `https://localhost/prometheus`
- Traefik dashboard: `https://localhost/dashboard/`

If you use local self-signed certs, run `curl` with `-k`.

## Documentation portal

### Docker mode (recommended)

```bash
cd zyrabit-slm
docker compose --profile docs up -d docs-portal
```

Open: `https://localhost/docs-portal`

### Local Node mode

```bash
cd docs-portal
pnpm install
pnpm start
```

Open: `http://localhost:3001`

## Architecture validation

```bash
./scripts/run_final_tests.sh
k6 run validation/k6/chat_steady.js
k6 run validation/k6/chat_spike.js
k6 run validation/k6/chat_soak.js
k6 run validation/k6/ingest_concurrent.js
```

Local PR checklist: `validation/pr-checklist.md`

## Docs and contribution

- Architecture Guide: [HEXAGONAL_ARCHITECTURE.md](file:///Users/abrahamgomez/tech/zyrabit-SLM/zyrabit-slm/api-rag/app/HEXAGONAL_ARCHITECTURE.md)
- Agent Governance: [AGENTS.md](file:///Users/abrahamgomez/tech/zyrabit-SLM/.gemini/AGENTS.md)
- Contribution rules (ES): `CONTRIBUTING.md`
- Contribution rules (EN): `CONTRIBUTING_EN.md`
- Backend technical doc (ES): `zyrabit-slm/README.md`
- Backend technical doc (EN): `zyrabit-slm/README_EN.md`

## GitHub Actions (CI)

This repository includes workflows in `.github/workflows` to:

- enforce contribution policy (PR base branch must be `beta`)
- run automated tests
- run dependency security audits

## Docker Hub & Air-Gapped Deployment

Zyrabit SLM resides on Docker Hub:
[hub.docker.com/r/zyrabitcore/zyrabit-slm](https://hub.docker.com/r/zyrabitcore/zyrabit-slm)

### 📥 Descarga de Imágenes y Modelos

1. **Imagen de la Consola:**
   ```bash
   docker pull zyrabitcore/zyrabit-slm:latest
   ```

2. **Descarga del Modelo (SLM):**
   Si usas el motor integrado (`slm-engine`), descarga el modelo deseado:
   ```bash
   docker exec -it slm-engine ollama pull llama3
   ```

### 🛡️ Despliegue Air-Gapped (Sin Internet)

Para entornos restringidos donde no hay acceso a internet, debes pre-poblar los modelos y mapear el volumen al motor:

1. Descarga el modelo en una máquina con internet.
2. Copia la carpeta de modelos a tu servidor seguro.
3. Mapea el volumen en el arranque:
   ```bash
   docker run -d \
     -v /tu/ruta/local/models:/root/.ollama \
     --name slm-engine \
     ollama/ollama:latest
   ```

> [!IMPORTANT]
> Asegúrate de que los blobs del modelo ya existan en esa ruta para evitar el intento de descarga automática durante el primer arranque.

## License

MIT © Zyrabit
