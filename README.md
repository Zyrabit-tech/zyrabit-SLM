# Zyrabit LLM Secure Suite

![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![Docker](https://img.shields.io/badge/docker-compose-ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)

## 📖 Descripción del proyecto

**Zyrabit** es una solución completa de IA **Zero‑Trust** que combina:
- Un **servidor Ollama** local.
- Un **cliente Python** (`secure_agent.py`) que **sanitiza** cualquier prompt antes de enviarlo al modelo, evitando fugas de datos sensibles (PII, tarjetas, montos).
- Un **dashboard interactivo** construido con **Streamlit** (`app.py`) que muestra el prompt original y el prompt sanitizado, y visualiza la respuesta del modelo.
- Un **entorno Docker‑Compose** que orquesta el API RAG, Ollama, ChromaDB, Prometheus y Grafana.

El objetivo es demostrar cómo integrar **ciberseguridad ofensiva** en flujos de IA generativa sin sacrificar la usabilidad.

---

## 💰 Por qué Zyrabit (Value Proposition)

| Característica | 🚫 IA Pública (ChatGPT/Claude) | ✅ Zyrabit (Local & Secure) |
| :--- | :--- | :--- |
| **Fuga de Datos** | Alto Riesgo (Tus datos entrenan sus modelos) | **Cero Riesgo** (Sanitización local + Air-Gapped) |
| **Costos Nube** | Recurrentes ($20/mes por usuario) | **$0 / mes** (Corre en tu propio hardware) |
| **Hardware** | Depende de servidores externos | **Optimizado** (Corre en CPU/GPU de consumo) |
| **Privacidad** | Caja Negra | **Auditable** (Código Abierto 100%) |

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

```mermaid
graph TD
    subgraph "Cliente Seguro (Python Local)"
        User((👤 Usuario))
        Agent[🕵️ secure_agent.py<br/>(Sanitizer Regex/NER)]
        UI[🖥️ app.py<br/>(Streamlit Dashboard)]
    end

    subgraph "Zyrabit Core (Docker Network)"
        API[⚡ api-rag<br/>(FastAPI Gateway)]
        LLM[🧠 llm-server<br/>(Ollama - Phi3)]
        VectorDB[(🗄️ ChromaDB<br/>Memoria Vectorial)]
        Monitor[📊 Grafana + Prometheus<br/>Observabilidad]
    end

    User --> UI
    UI -->|1. Prompt Crudo| Agent
    Agent -->|2. Datos Redacted| API
    API -->|3. Query Vectorial| VectorDB
    VectorDB -->|4. Contexto| API
    API -->|5. Prompt Final| LLM
    LLM -->|6. Respuesta| API
    API -->|7. Display Seguro| UI

    style Agent fill:#ff9900,stroke:#333,stroke-width:2px
    style LLM fill:#99ff99,stroke:#333,stroke-width:2px
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

## 🚑 Troubleshooting

| Problema | Solución Posible |
| :--- | :--- |
| **Error: Connection refused** | Asegúrate de que Docker esté corriendo (`docker ps`) y que el puerto 11434 esté libre. |
| **Modelo no responde** | Ejecuta `./setup_ollama.sh` nuevamente para verificar que `phi3` se descargó correctamente. |
| **Streamlit no encontrado** | Revisa tu PATH o ejecuta `python3 -m streamlit run app.py`. |
| **Permisos denegados** | Ejecuta `chmod +x setup_ollama.sh` antes de correr el script. |

---

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT**. Puedes usar, modificar y distribuir el código, incluso con fines comerciales, siempre que mantengas el aviso de licencia original.

---

## 🙌 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un *pull request* describiendo los cambios y asegurándote de que todas las pruebas pasen.

---

## 📞 Contacto

**Zyrabit Systems** – https://zyrabit.com


🚧 PUBLIC BETA / EARLY ACCESS Este proyecto está en desarrollo activo. La arquitectura Core es estable, pero las interfaces pueden cambiar. Buscamos contribuidores valientes que quieran probar la "Seguridad Ofensiva" en sus propios entornos. Si rompes algo, abre un Issue. Si te gusta, danos una