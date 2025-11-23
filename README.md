# Zyrabit LLM Secure Suite

![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![Docker](https://img.shields.io/badge/docker-compose-ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)

## 📖 Descripción del proyecto

**Zyrabit** es una solución completa de IA **Zero‑Trust** que combina:
- Un **servidor Ollama** local (modelo `phi3` – sustituto de `mistral`).
- Un **cliente Python** (`secure_agent.py`) que **sanitiza** cualquier prompt antes de enviarlo al modelo, evitando fugas de datos sensibles (PII, tarjetas, montos).
- Un **dashboard interactivo** construido con **Streamlit** (`app.py`) que muestra el prompt original y el prompt sanitizado, y visualiza la respuesta del modelo.
- Un **entorno Docker‑Compose** que orquesta el API RAG, Ollama, ChromaDB, Prometheus y Grafana.

El objetivo es demostrar cómo integrar **ciberseguridad ofensiva** en flujos de IA generativa sin sacrificar la usabilidad.

---

## ✨ Características principales

- **Sanitización automática** de correos, números de tarjetas de crédito y montos en dólares usando expresiones regulares.
- **Exposición del puerto Ollama (11434)** para que scripts locales puedan comunicarse con el modelo.
- **Instalación automática** del modelo `phi3` mediante el script `setup_ollama.sh`.
- **Interfaz gráfica** con Streamlit que muestra lado‑a‑lado el texto antes y después de la sanitización.
- **Monitoreo** con Prometheus y Grafana (puertos 9091 y 3000).
- **Persistencia** de modelos y vectores mediante volúmenes Docker (`./ollama-models`, `./chroma-data`).

---

## 🏗️ Arquitectura

```
┌─────────────────────┐   ┌─────────────────────┐
│  api-rag (FastAPI) │←─▶│   llm-server (Ollama)│
│  (RAG endpoint)    │   │   model: phi3       │
└─────────────────────┘   └─────────────────────┘
          │                         │
          ▼                         ▼
   ┌───────────────┐        ┌───────────────┐
   │ vector-db     │        │ prometheus    │
   │ (ChromaDB)   │        │ & grafana     │
   └───────────────┘        └───────────────┘
```

---

## 🚀 Instalación y puesta en marcha

### 1️⃣ Prerrequisitos

- **Docker & Docker‑Compose**
- **Python 3.9+**
- **pip** (se usará `python3 -m pip` para evitar problemas de PATH)

### 2️⃣ Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/zyrabit-llm.git
cd zyrabit-llm
```

### 3️⃣ Instalar dependencias Python

```bash
python3 -m pip install --user requests streamlit watchdog
```
> *Nota:* `streamlit` se instaló en `~/Library/Python/3.9/bin`. Añade esa ruta a tu `$PATH` si deseas usar el comando directamente:
```bash
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
```

### 4️⃣ Levantar los contenedores Docker

```bash
docker-compose up -d
```
Esto creará los servicios `api-rag`, `llm-server`, `vector-db`, `prometheus` y `grafana`.

### 5️⃣ Descargar el modelo

Ejecuta el script de setup (descarga automática del modelo `phi3`):

```bash
chmod +x setup_ollama.sh
./setup_ollama.sh
```
El script verifica si el modelo ya está instalado y, de no ser así, lo descarga.

### 6️⃣ Probar el cliente seguro

```bash
python3 secure_agent.py
```
Deberías ver dos casos de prueba: una pregunta inocente y una con datos sensibles que son redacted.

### 7️⃣ Ejecutar la UI Streamlit

```bash
streamlit run app.py --server.headless true
```
Abre `http://localhost:8501` en tu navegador. La barra lateral muestra la configuración y el panel principal permite introducir prompts y ver el texto sanitizado y la respuesta del modelo.

---

## 📋 Tareas pendientes

- [ ] **Mejorar la DLP**: sustituir expresiones regulares por un modelo NER local para detección más robusta.
- [ ] **Integrar autenticación** en la UI (OAuth / API key).
- [ ] **Añadir pruebas unitarias** para `sanitize_input` y la capa de red.
- [ ] **Documentar la API RAG** (`api-rag` endpoints) en Swagger.
- [ ] **Configurar CI/CD** para despliegues automáticos en Vercel/Firebase.
- [ ] **Actualizar README** con screenshots de la UI y diagramas de arquitectura.

---

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT**. Puedes usar, modificar y distribuir el código, incluso con fines comerciales, siempre que mantengas el aviso de licencia original.

---

## 🙌 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un *pull request* describiendo los cambios y asegurándote de que todas las pruebas pasen.

---

## 📞 Contacto

**Zyrabit Systems** – https://zyrabit.com

---

*Este README fue generado automáticamente y actualizado con los últimos cambios del proyecto.*

https://github.com/mlco2/codecarbon/blob/master/CONTRIBUTING.md