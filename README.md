# Zyrabit SLM Secure Suite (v1.0)

[![English](https://img.shields.io/badge/lang-English-blue.svg)](README_EN.md)
[![Python](https://img.shields.io/badge/python-3.12%20recommended-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker--compose-ready-green.svg)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Suite local de IA con **SLM + RAG + capa de seguridad Zero-Trust**.

## Qué levanta este proyecto

- `traefik`: entrypoint HTTPS local (`https://localhost`)
- `api-rag`: API principal (chat, ingest, mcp, webhooks)
- `slm-engine`: inferencia local con Ollama
- `vector-db`: ChromaDB para conocimiento
- `prometheus` + `grafana`: métricas y dashboards
- `docs-portal` (opcional)
- `n8n` (opcional)

Redes Docker:

- `frontend-network`
- `backend-network`
- `model-network` (`internal: true`)

## Instalación de Ollama (Nativo vs Docker)

Por defecto, Zyrabit levanta Ollama dentro de Docker (`slm-engine`). Sin embargo, para aprovechar al máximo tu hardware (GPU/Metal) en Mac o Windows, y evitar problemas de rendimiento o configuración de red, **recomendamos instalar Ollama de forma nativa** (como subproceso del sistema operativo).

### 🍎 macOS
1. Descarga Ollama desde [ollama.com/download/mac](https://ollama.com/download/mac).
2. Descomprime e instala la aplicación `Ollama.app`.
3. Abre la aplicación; Ollama se ejecutará en segundo plano (tendrás un icono en la barra de menú).
4. El servicio estará disponible internamente en `http://localhost:11434`.

### 🪟 Windows
1. Descarga el instalador desde [ollama.com/download/windows](https://ollama.com/download/windows).
2. Ejecuta `OllamaSetup.exe`.
3. Ollama se iniciará automáticamente y estará disponible en la bandeja del sistema.
4. El servicio estará disponible internamente en `http://localhost:11434`.

### 🐧 Ubuntu / Linux
Puedes usar la opción de Docker que viene por defecto, o instalarlo nativamente ejecutando este comando en tu terminal:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### ⚙️ Configurar Zyrabit para usar Ollama Nativo
Si decides usar la versión nativa, dile a Zyrabit dónde encontrar a Ollama editando el archivo `zyrabit-brain-api/.env` (cópialo de `example.env` si no lo has hecho):

- **Mac / Windows**:
  ```env
  INFERENCE_PROVIDER=ollama_host
  SLM_URL=http://host.docker.internal:11434/api/generate
  ```
- **Linux** (Usa la IP de tu host de docker, ej. `172.17.0.1` o `localhost` si ejecutas sin Docker):
  ```env
  INFERENCE_PROVIDER=ollama_host
  SLM_URL=http://172.17.0.1:11434/api/generate
  ```

*(Opcional) Una vez configurado de esta forma, puedes detener/comentar el servicio `slm-engine` en tu `docker-compose.yml` para ahorrar memoria.*

## Arranque rápido (UI + API)

1. Prerrequisitos:

```bash
docker --version
docker compose version
python3 --version
```

2. Instalar dependencias Python locales:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Levantar stack backend:

```bash
chmod +x zyra-up.sh
./zyra-up.sh doctor
./zyra-up.sh start
```

4. Levantar UI Streamlit:

```bash
source .venv/bin/activate
streamlit run slm_console.py
```

UI: `http://localhost:8501`

## Verificación funcional (end-to-end)

### 1) Salud del backend

```bash
curl -k https://localhost/health
```

Debe regresar `{"status":"ok", ...}`.

### 2) Chat normal

```bash
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"Explica la arquitectura de Zyrabit"}'
```

Debes ver `metadata.route_decision`, `rag_hits` y `latency_ms`.

### 3) Gatekeeper (rechazo de contenido fuera de política)

```bash
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"comprar viagra barato ahora"}'
```

Debe responder error `400` con `detail` (ruta `reject_query`).

### 4) Cambio de tokens por sanitización (PII)

```bash
python secure_agent.py "Mi correo es juan@example.com y mi cuenta es 4532-1234-5678-9012"
```

El pipeline anonimiza entidades (ejemplo: `<USER_EMAIL_1>`) antes de inferencia y restaura al responder.

### 5) Métricas de tokens y seguridad

```bash
curl -k https://localhost/metrics | grep zyrabit_token_usage_total
curl -k https://localhost/metrics | grep zyrabit_token_latency_ms_per_token
curl -k https://localhost/metrics | grep zyrabit_security_hits_total
```

### 🧠 Personalizar el System Prompt (Agent)

La personalidad del Agente de RAG (SLM) y sus reglas están definidas en un archivo externo montado dinámicamente. Esto te permite modificar la conducta del asistente en caliente sin necesidad de reconstruir la imagen de Docker.

1. Abre y edita el archivo: `zyrabit-brain-api/prompts/agent.md`.
2. Guarda los cambios. El backend los tomará en cuenta en las peticiones posteriores automáticamente.
   
*(Nota: El archivo se ignora en los commits locales mediante `.gitignore` para no pisar la configuración de cada usuario. Si necesitas restablecerlo, clona o copia el contenido de `prompts/agent.example.md`)*.

## Cómo abrir cada componente local

- UI chat: `http://localhost:8501`
- API docs: `https://localhost/docs`
- Grafana: `https://localhost/grafana`
- Prometheus: `https://localhost/prometheus`
- Traefik dashboard: `https://localhost/dashboard/`

Si usas certificados self-signed en local, utiliza `-k` en `curl`.

## Portal de documentación

### Opción Docker (recomendada)

```bash
cd zyrabit-brain-api
docker compose --profile docs up -d docs-portal
```

Abrir: `https://localhost/docs-portal`

### Opción local (Node)

```bash
cd docs-portal
pnpm install
pnpm start
```

Abrir: `http://localhost:3001`

## Validación de arquitectura

```bash
./scripts/run_final_tests.sh
k6 run validation/k6/chat_steady.js
k6 run validation/k6/chat_spike.js
k6 run validation/k6/chat_soak.js
k6 run validation/k6/ingest_concurrent.js
```

Checklist local PR: `validation/pr-checklist.md`

## Documentación y contribución

- Reglas de contribución (ES): `CONTRIBUTING.md`
- Contribution rules (EN): `CONTRIBUTING_EN.md`
- Backend técnico (ES): `zyrabit-brain-api/README.md`
- Backend technical (EN): `zyrabit-brain-api/README_EN.md`

## GitHub Actions (CI)

Este repositorio incluye workflows en `.github/workflows` para:

- validar política de PR (base branch `beta`)
- ejecutar tests automáticos
- ejecutar auditoría de dependencias

## Licencia

MIT © Zyrabit
