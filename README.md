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
   chmod +x setup_slm.sh
   ./setup_slm.sh   # verifica Docker, arranca slm-engine y descarga phi3, kimi‑k2‑thinking:cloud y mxbai‑embed‑large
   ```
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

El agente mostrará el prompt original, el prompt sanitizado y la respuesta del modelo.

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