# Zyrabit SLM Secure Suite (v1.0‑beta)

[![English](https://img.shields.io/badge/lang-English-blue.svg)](README_EN.md)
![Python](https://img.shields.io/badge/python-v3.10%2B-blue.svg)
![Docker](https://img.shields.io/badge/docker--compose-ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

---

## 📖 Descripción

**Zyrabit SLM Secure Suite** es una solución de IA local que combina un modelo de lenguaje pequeño (**Small Language Models - SLMs**) con un motor de recuperación‑aumentada (RAG) y una capa de **Zero‑Trust**.

### 🧬 Nuestra Filosofía
*   **Eficiencia**: Ejecución optimizada para hardware de consumo (Mac M1/M2, Consumer GPUs).
*   **Velocidad**: Menor latencia gracias a modelos compactos (Phi-3, Mistral).
*   **Soberanía**: Tus datos nunca salen de tu infraestructura. Todo corre localmente.

---

## 🛠️ Entorno Validado

| Plataforma | CPU | RAM | OS |
|------------|-----|-----|----|
| MacBook Pro (M1 Pro) | 8‑core | 16 GB | macOS Sequoia 15.1 |
| Linux (Ubuntu 22.04) | 4‑core | 8 GB | - |
| Windows (WSL2) | 4‑core | 8 GB | - |

> **Nota Windows:** Use WSL2 para ejecutar Docker y los scripts.

---

## 📦 Instalación

Instalación ultra-rápida (estilo bootstrap):

```bash
curl -sSL https://zyrabit.com/install.sh | bash
```

O instalación local:

1. **Prerequisitos**
   - Docker & Docker‑Compose
   - Python 3.10 +
   - `git` (opcional)
2. **Clonar el repositorio**
   ```bash
   git clone https://github.com/Zyrabit-tech/zyrabit-llm.git
   cd zyrabit-SLM
   ```
3. **Entorno virtual**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   # .venv\Scripts\activate   # Windows
   pip3 install -r requirements.txt
   ```
4. **Infraestructura**
   ```bash
   cd zyrabit-brain-api
   docker compose up -d   # levanta slm-engine, vector‑db y api‑rag
   cd ..
   ```
5. **Descargar modelos obligatorios**
   ```bash
   chmod +x zyra-up.sh
   ./zyra-up.sh
   ```
   El script detecta NVIDIA/Metal/CPU y usa `qwen2.5:7b` por defecto (`qwen2.5:1.5b` en equipos con menos RAM).
6. **Ejecutar la UI**
   ```bash
   streamlit run slm_console.py
   ```
   Accede a `http://localhost:8501`.

---

## 🚀 Uso rápido

```bash
# CLI segura
python secure_agent.py "Mi email es juan@example.com y mi saldo es $1,200.00"
```

El agente aplica anonimización reversible por tokens (`<USER_EMAIL_1>`, etc.) antes de inferencia y restaura el resultado para el usuario.

## 🔐 Endurecimiento de red y entrada

- Reverse proxy con Traefik como punto de entrada único (`https://localhost`).
- Redirección HTTP→HTTPS y rate limiting para endpoints críticos.
- Segmentación de redes Docker:
  - `frontend-network`
  - `backend-network`
  - `model-network` con `internal: true`

## 📈 Observabilidad

Endpoint Prometheus real en `/metrics`, incluyendo:

- `zyrabit_token_latency_ms_per_token`
- `zyrabit_token_usage_total`
- `zyrabit_security_hits_total`

## 🔌 MCP Bridge

- Config estándar: `mcp/config.json`
- Endpoint en API: `GET /mcp/config.json`
- JSON-RPC MCP: `POST /mcp`
- Todas las operaciones del bridge se sanitizan antes de exponerse.

## 📚 Portal de documentación

Se incluye contenedor opcional de docs (Docusaurus):

```bash
cd zyrabit-brain-api
docker compose --profile docs up -d docs-portal
```

Además, se incluye `llms-full.md` como referencia técnica optimizada para agentes de IA.

---

## 🧪 Tests

Ejecuta la suite de pruebas con:
```bash
pytest -q
```
Los tests cubren la sanitización de PII y la correcta respuesta del backend.

---

## 📜 Licencia

MIT © Zyrabit 2025