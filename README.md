# Zyrabit SLM Secure Suite (v1.0-beta)

[![English](https://img.shields.io/badge/lang-English-blue.svg)](README_EN.md)
![Python](https://img.shields.io/badge/python-v3.10%2B-blue.svg)
![Docker](https://img.shields.io/badge/docker--compose-ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

---

## Descripcion

**Zyrabit SLM Secure Suite** es una solucion de IA local que combina **Small Language Models (SLMs)** con un motor RAG y una capa de seguridad **Zero-Trust**.

### Nuestra filosofia

- **Eficiencia**: ejecucion optimizada para hardware de consumo (Mac M1/M2, GPUs de consumo).
- **Velocidad**: baja latencia con modelos compactos.
- **Soberania**: tus datos no salen de tu infraestructura.

---

## Entorno validado

| Plataforma | CPU | RAM | OS |
|------------|-----|-----|----|
| MacBook Pro (M1 Pro) | 8-core | 16 GB | macOS Sequoia 15.1 |
| Linux (Ubuntu 22.04) | 4-core | 8 GB | - |
| Windows (WSL2) | 4-core | 8 GB | - |

> Nota Windows: usa WSL2 para ejecutar Docker y scripts.

---

## Instalacion

Instalacion bootstrap:

```bash
curl -sSL https://zyrabit.com/install.sh | bash
```

Instalacion local:

1. **Prerequisitos**
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
   # .venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```
4. **Infraestructura**
   ```bash
   chmod +x zyra-up.sh
   ./zyra-up.sh install
   ```
5. **Modos del instalador**
   ```bash
   ./zyra-up.sh doctor
   ./zyra-up.sh start
   ./zyra-up.sh install
   ```
   Scripts oficiales:
   - `install.sh`: bootstrap remoto/local (clona y ejecuta `zyra-up.sh install`)
   - `zyra-up.sh`: instalador principal y orquestador del stack

   Descarga manual de modelos:
   ```bash
   docker compose -f zyrabit-brain-api/docker-compose.yml up -d slm-engine
   docker compose -f zyrabit-brain-api/docker-compose.yml exec -T slm-engine ollama pull qwen2.5:7b
   docker compose -f zyrabit-brain-api/docker-compose.yml exec -T slm-engine ollama pull mxbai-embed-large
   ```

6. **Ejecutar UI**
   ```bash
   streamlit run slm_console.py
   ```
   URL: `http://localhost:8501`

## Air-Gapped Installation (prioridad alta)

Para entornos US/EU con red cerrada:

1. En una maquina con internet, descarga imagenes:
   ```bash
   docker pull traefik:latest
   docker pull ollama/ollama:latest
   docker pull chromadb/chroma:latest
   docker pull prom/prometheus:latest
   docker pull grafana/grafana:latest
   docker pull n8nio/n8n:latest
   ```
2. Exporta las imagenes a archivos tar:
   ```bash
   docker save -o zyrabit-images.tar \
     traefik:latest ollama/ollama:latest chromadb/chroma:latest \
     prom/prometheus:latest grafana/grafana:latest n8nio/n8n:latest
   ```
3. Mueve `zyrabit-images.tar` por USB (o media controlada) al servidor aislado.
4. Importa las imagenes en el servidor aislado:
   ```bash
   docker load -i zyrabit-images.tar
   ```
5. Levanta el stack sin salida a internet:
   ```bash
   ./zyra-up.sh start
   ```

Alternativa enterprise: usar un registry local (Harbor/Nexus/Artifactory), replicar imagenes firmadas, y hacer `docker pull` solo desde registry interno.

---

## Uso rapido

```bash
python secure_agent.py "Mi email es juan@example.com y mi saldo es $1,200.00"
```

## Endurecimiento de red e ingreso

- Traefik como punto de entrada unico (`https://localhost`).
- Segmentacion de redes Docker (`frontend-network`, `backend-network`, `model-network` interno).
- Servicios de observabilidad e integraciones publicados por rutas Traefik (`/grafana`, `/prometheus`, `/n8n`).
- La observabilidad requiere variables de auth basica (`PROMETHEUS_BASIC_AUTH`, `GRAFANA_BASIC_AUTH`).

## Portal de documentacion

```bash
cd zyrabit-brain-api
docker compose --profile docs up -d docs-portal
```

## Mapa de documentacion (sin duplicidad)

- `README.md`: onboarding y uso global (ES).
- `README_EN.md`: espejo en ingles del root.
- `zyrabit-brain-api/README.md`: operacion tecnica backend (ES).
- `zyrabit-brain-api/README_EN.md`: espejo tecnico backend (EN).

## Tests

```bash
cd zyrabit-brain-api/api-rag
python3 -m pytest -q
```

## Licencia

MIT © Zyrabit 2025
