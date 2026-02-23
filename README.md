# Zyrabit SLM Secure Suite (v1.0-beta)

[![English](https://img.shields.io/badge/lang-English-blue.svg)](README_EN.md)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker--compose-ready-green.svg)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)](#arquitectura)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#tests)

---

## Descripción

**Zyrabit SLM Secure Suite** es una solución de IA local que combina **Small Language Models (SLMs)** con un motor RAG y una capa de seguridad **Zero-Trust**.

### Filosofía

| Principio | Descripción |
|-----------|-------------|
| **Eficiencia** | Ejecución optimizada para hardware de consumo (Mac M1/M2, GPUs de consumo) |
| **Velocidad** | Baja latencia con modelos compactos |
| **Soberanía** | Tus datos no salen de tu infraestructura |

---

## Entorno validado

| Plataforma | CPU | RAM | OS |
|------------|-----|-----|-----|
| MacBook Pro (M1 Pro) | 8-core | 16 GB | macOS Sequoia 15.1 |
| Linux (Ubuntu 22.04) | 4-core | 8 GB | - |
| Windows (WSL2) | 4-core | 8 GB | - |

> **Nota Windows:** usa WSL2 para ejecutar Docker y scripts.

---

## Instalación

### Bootstrap remoto

```bash
curl -sSL https://zyrabit.com/install.sh | bash
```

### Instalación local

1. **Prerrequisitos**
   - Docker y Docker Compose
   - Python 3.10+
   - `git` (opcional)

2. **Clonar repositorio**
   ```bash
   git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
   cd zyrabit-SLM
   ```

3. **Entorno virtual**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   # .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

4. **Infraestructura**
   ```bash
   chmod +x zyra-up.sh
   ./zyra-up.sh install
   ```

5. **Modos del instalador**
   ```bash
   ./zyra-up.sh doctor    # Diagnóstico del entorno
   ./zyra-up.sh start    # Levantar stack
   ./zyra-up.sh install  # Instalación completa
   ```

   **Scripts oficiales:**
   - `install.sh`: bootstrap remoto/local (clona y ejecuta `zyra-up.sh install`)
   - `zyra-up.sh`: instalador principal y orquestador del stack

6. **Descarga manual de modelos**
   ```bash
   docker compose -f zyrabit-brain-api/docker-compose.yml up -d slm-engine
   docker compose -f zyrabit-brain-api/docker-compose.yml exec -T slm-engine ollama pull qwen2.5:7b
   docker compose -f zyrabit-brain-api/docker-compose.yml exec -T slm-engine ollama pull mxbai-embed-large
   ```

7. **Ejecutar UI**
   ```bash
   streamlit run slm_console.py
   ```
   URL: `http://localhost:8501`

---

## Uso rápido

### API Chat (local)

```bash
# Usa -k para ignorar certificado self-signed en desarrollo
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"¿Qué es Zyrabit y cuál es su arquitectura?"}'
```

Ver más ejemplos: `zyrabit-brain-api/docs/CURL_EXAMPLES.md`

### Agente seguro

```bash
python secure_agent.py "Mi email es juan@example.com y mi saldo es $1,200.00"
```

---

## Desarrollo local vs producción

| Aspecto | Local | Producción |
|---------|-------|------------|
| **TLS** | Traefik usa HTTPS con cert self-signed. Usa `curl -k` para pruebas | Certificado válido (Let's Encrypt, etc.) |
| **URL base** | `https://localhost` | Tu dominio |
| **Observabilidad** | Prometheus/Grafana en `/prometheus`, `/grafana` | Idem, con auth básica |

El stack está diseñado para funcionar igual en ambos entornos. En local, `-k` ignora la verificación del certificado.

---

## Air-Gapped Installation

Para entornos con red cerrada (US/EU):

1. En una máquina con internet, descarga imágenes:
   ```bash
   docker pull traefik:latest ollama/ollama:latest chromadb/chroma:latest \
     prom/prometheus:latest grafana/grafana:latest n8nio/n8n:latest
   ```

2. Exporta a archivos tar:
   ```bash
   docker save -o zyrabit-images.tar \
     traefik:latest ollama/ollama:latest chromadb/chroma:latest \
     prom/prometheus:latest grafana/grafana:latest n8nio/n8n:latest
   ```

3. Mueve `zyrabit-images.tar` por USB al servidor aislado.

4. Importa en el servidor:
   ```bash
   docker load -i zyrabit-images.tar
   ```

5. Levanta el stack:
   ```bash
   ./zyra-up.sh start
   ```

---

## Endurecimiento de red

- **Traefik** como punto de entrada único (`https://localhost`)
- **Segmentación de redes** Docker: `frontend-network`, `backend-network`, `model-network` (interno)
- **Observabilidad** en rutas Traefik: `/grafana`, `/prometheus`, `/n8n`
- Variables requeridas: `PROMETHEUS_BASIC_AUTH`, `GRAFANA_BASIC_AUTH` (ver `zyrabit-brain-api/example.env`)

---

## Portal de documentación

```bash
cd zyrabit-brain-api
docker compose --profile docs up -d docs-portal
```

---

## Mapa de documentación

| Archivo | Contenido |
|---------|-----------|
| `README.md` | Onboarding y uso global (ES) |
| `README_EN.md` | Espejo en inglés |
| `zyrabit-brain-api/README.md` | Operación técnica backend (ES) |
| `zyrabit-brain-api/README_EN.md` | Espejo técnico backend (EN) |

---

## Tests

**Unit e integración:**
```bash
cd zyrabit-brain-api/api-rag
python3 -m pytest -q
```

**Prueba final** (imágenes, ingesta, API, RAG):
```bash
./scripts/run_final_tests.sh
```

---

## Licencia

MIT © Zyrabit 2025
