RAG-Stack-Local 🚀

Tu propio "cerebro" de IA, 100% open-sources

## Actualizaciones de endurecimiento (MVP)

- **PII Pipeline con sharding**: anonimización reversible por tokens antes de tocar el SLM.
- **Observabilidad real**: `/metrics` ahora exporta métricas Prometheus útiles de seguridad y eficiencia.
- **Aislamiento de red**: separación `frontend-network`, `backend-network`, `model-network` (`internal: true`).
- **Guardían de entrada**: Traefik como único ingreso con HTTPS local y rate limiting.
- **MCP bridge**: endpoints `/mcp/config.json` y `/mcp` para integración compatible JSON-RPC.

## Endpoints clave

- `GET /health`
- `POST /v1/chat`
- `POST /v1/ingest`
- `GET /metrics`
- `GET /mcp/config.json`
- `POST /mcp`

Este proyecto te da el stack completo para correr un sistema de Retrieval-Augmented Generation (RAG) en tu propia máquina o servidor. Olvídate de APIs de terceros, facturas impredecibles y de mandar tus datos sensibles a la nube de alguien más.

Aquí, tú tienes el control.

🧠 La Filosofía: Por Qué Construimos Esto

Vivimos una revolución de IA, pero la mayoría de las soluciones nos piden sacrificar el control por la conveniencia. Este proyecto se basa en 4 principios:

Control Total (Self-Hosted): Tus modelos, tus datos, tus reglas. Todo corre en tu hardware (local o en la nube que tú elijas). No más dependencia de APIs externas.

Arquitectura Desacoplada: Inspirado en microservicios. El "Cerebro" (API), el "Músculo" (SLM) y la "Memoria" (VectorDB) son contenedores separados. ¿Necesitas escalar la GPU? Escala solo el "Músculo". ¿Quieres cambiar de Chroma a Qdrant? Cambia solo la "Memoria".

Portabilidad (Docker): docker compose up. Funciona en el Mac M2 de tu dev, funciona en un Droplet de DigitalOcean con GPU, y funciona en tu server bare-metal. Sin drama.

Observabilidad Primero: No volamos a ciegas. El stack incluye Prometheus y Grafana desde el día cero. Si es lento, sabrás por qué es lento (CPU, VRAM, I/O...).

🏗️ Arquitectura del Stack

Este es el plan. Usamos docker-compose para orquestar 5 servicios que se hablan entre sí en una red interna.




🛠️ Tech Stack

API (Cerebro): FastAPI (Python)

Servidor SLM (Músculo): Ollama

VectorDB (Memoria): ChromaDB

Orquestación: Docker-Compose

Monitoreo: Prometheus & Grafana

🚀 Cómo Empezar

Prerrequisitos

Docker

Docker Compose

git

(Opcional, pero recomendado) Un host con GPU NVIDIA y los drivers de NVIDIA + NVIDIA Container Toolkit.

Instalación

Clona el repositorio:

git clone [https://github.com/TU_USUARIO/TU_REPO.git](https://github.com/TU_USUARIO/TU_REPO.git)
cd TU_REPO


Crea los directorios para los volúmenes:
(Esto evita problemas de permisos con Docker)

mkdir -p ollama-models
mkdir -p chroma-data


Levanta el stack:

docker compose up -d


Baja tu primer modelo (ej: Phi-3):

docker compose exec SLM-server ollama pull phi3


(Revisa la sección de "Elegir tu Modelo" para más opciones)

Carga tus documentos (Ingesta):

Coloca tus archivos (PDFs, .txt, .md) en una carpeta (ej. ./documentos-fuente).

Instala las dependencias para el script de ingesta (en tu máquina local, no en Docker):

pip install -r ingest/requirements.txt


Ejecuta el script (asegúrate que vector-db expone el puerto 8001:8000 en tu docker-compose.yml para esto):

python3 ingest/ingest.py --source_dir ./documentos-fuente


Prueba el API

Una vez que tus documentos estén cargados, puedes hacer una consulta:

curl -X POST http://localhost:8080/v1/chat \
     -H "Content-Type: application/json" \
     -d '{
           "text": "¿Cuál es la filosofía de Clean Architecture?"
         }'


Revisa tus dashboards:

Prometheus: http://localhost:9090

Grafana: http://localhost:3000

🤖 Eligiendo tu Modelo: Local vs. MVP vs. Producción

No todos los modelos son iguales. Elige el motor adecuado para tu carrera.

Etapa

Objetivo

Modelos Recomendados (Ejemplos)

Hardware Mínimo

Local (Dev)

Velocidad, fricción CERO.

phi3:mini, deepseek-coder:6.7b-instruct-q4

8GB RAM (CPU) / 8GB VRAM (GPU)

MVP (Team)

Validar valor, buen balance.

qwen:14b-chat-q5_K_M, deepseek-coder:33b-instruct-q4

16-32GB VRAM (GPU Mediana: T4, A10G)

Producción

Performance, razonamiento SOTA.

codestral:latest, qwen:72b-chat-q4_K_M

40GB+ VRAM (GPU Grande: A100, H100)

💡 Conceptos Clave: Pesos vs. Contexto

Para entender RAG, debes entender esta diferencia:

Pesos (Parámetros): Es el Cerebro del SLM. Es el conocimiento permanente que el modelo "aprendió" durante su entrenamiento (meses de cómputo en supercomputadoras). Es estático y pesado (gigas).

Analogía: La educación de un doctor en la facultad de medicina. Sabe qué es la diabetes, el cáncer y cómo funciona el cuerpo humano.

Contexto (Ventana de Contexto): Es la Memoria RAM del SLM. Es la información temporal que le das en este instante. Es volátil y se limpia con cada nueva petición.

Analogía: El expediente del paciente que le das al doctor.

Por qué RAG es una genialidad: No intentamos re-entrenar al doctor (modificar los pesos). Simplemente le pasamos el expediente correcto (el contexto de tu VectorDB) junto con la pregunta. El modelo usa su conocimiento (pesos) para analizar la información temporal (contexto) y darte una respuesta experta.

📜 Filosofía de Código y Pruebas


Stateless API: El api-rag NO debe guardar estado. Todo estado persistente vive en vector-db o ollama-models.

Configuración por Entorno: Cero hardcoding. URLs, nombres de modelos y tokens se manejan con variables de entorno (.env y docker-compose.yml).

Lógica Clara: El código de prompting debe ser fácil de encontrar y modificar.

Pruebas

Un PR sin pruebas es un PR roto. Exigimos:

Unit Tests (Pytest): Prueba funciones puras (ej. chunkers, prompt_formatters). Mockea (simula) las llamadas a los servicios SLM-server y vector-db.

Integration Tests: Prueba el flujo completo. Usa un docker-compose.override.yml para levantar una base de datos de prueba y un modelo ligero, y confirma que el endpoint /query devuelve una respuesta.

Pruebas de Calidad (RAG): (Avanzado) Mantén un "set dorado" de preguntas y respuestas esperadas para medir la calidad de la recuperación (¿Encontró el chunk correcto?) y la calidad de la generación.

🤝 Cómo Contribuir (¡Eres bienvenido!)

Este es un proyecto open-source. Estamos felices de recibir forks, issues y Pull Requests.

El Proceso (Fork & Pull)

Habla primero: Si quieres agregar una feature grande, crea un Issue primero para discutirla.

Haz Fork del repositorio a tu propia cuenta de GitHub.

Crea una rama para tu feature: git checkout -b feat/mi-feature-genial

Programa (y añade pruebas, ¡por favor!).

Asegúrate que el linter pase (ej. black . y ruff .).

Haz un Pull Request desde tu rama a la rama main de este repositorio.

Llena la plantilla de PR: Describe qué hace tu PR, por qué es necesario y cómo podemos probarlo.

Revisa CONTRIBUTING.md para reglas más detalladas.

📄 Licencia

Este proyecto está bajo la Licencia MIT. Eres libre de usarlo, modificarlo y distribuirlo, incluso para uso comercial, siempre y cuando mantengas el aviso de licencia original.


![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![Docker](https://img.shields.io/badge/docker-compose-ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)