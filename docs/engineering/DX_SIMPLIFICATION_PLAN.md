# Plan DX / Simplificación — Zyrabit Platform

**Rama de trabajo:** `feat/unified-distribution` (base `beta`)  
**Fecha:** Septiembre 2026  
**Propósito:** hoja de ruta para maximizar developer experience y time-to-value sin perder el diferencial soberano (PII, citas, air-gap).

**Mapa de agentes + tools:** [`AGENT_TOOL_RUNTIME_MAP.md`](./AGENT_TOOL_RUNTIME_MAP.md).

> Copia canónica **versionada en git**. El archivo local `PLAN_STATUS_TEMPORAL.md` (gitignore) puede duplicar el §5 para trabajo de rama.

---

## Plan (prioridad)

**Estado:** activo en `feat/unified-distribution`  
**Objetivo:** time-to-first-value en **&lt;2–5 min** (Ollama en el host + 1 contenedor en `:8080`) para generar adopción sin perder el diferencial soberano.

### 5.1 Posicionamiento vs mercado

| Ellos ganan hoy | Nosotros debemos ganar |
|---|---|
| Chat UX / stars (Open WebUI ~150k, AnythingLLM ~60k) | **Confianza verificable**: PII antes del modelo, 0-egress, citas (“cita o calla”), audit |
| Workflows (Dify) | API + contenedor único para integradores |
| Time-to-chat | Time-to-**confianza** (PDF → respuesta citada sin fuga) |

Licencia MIT + runtime soberano (RAG + PII + obs + air-gap) es el espacio blanco. No pelear “UI más bonita” con Open WebUI; pelear el path de confianza.

### 5.2 Principios

1. **Un solo happy path** visible: `docker run` → `http://localhost:8080`.
2. **Defaults mínimos** (~3–5 env); el resto es Advanced.
3. **Lite vs Platform** = dos historias, mismo repo (no dos productos confusos en el README).
4. Compose multi-servicio, Traefik, Grafana, perfiles = **opt-in**, nunca el primer pantallazo.
5. Contributor path ≠ user path (`CONTRIBUTING` para devs; README para valor en minutos).

### 5.3 Diagnóstico actual (rama)

| Señal | Hecho |
|---|---|
| CLI | `zyra.sh` ~1333 líneas; wizard interactivo 4 pasos |
| Compose default | ~5 servicios bajo `zyrabit-slm/docker-compose.yml` (api, web, engine, db, mcp) |
| Env | `example.env` ~30 keys |
| Docs | README Option A (bien) vs Option B / Hub naming (`zyrabit-slm` vs `zyrabit-platform`) |
| All-in-One | Dockerfile raíz + Chroma embebido ✅ — compose default aún no alcanzó esa simplicidad |

### 5.4 Fases (checklist ejecutable)

#### Fase A — Docs (esta iteración / inmediato)
- [x] Dejar este plan en `PLAN_STATUS_TEMPORAL.md` (doc activo de la rama)
- [x] README: hero = Option A `docker run` + puerto único `:8080`; Option B demoted a Advanced/From source
- [x] README: enlace corto a este plan (sin meter el plan largo en el README)
- [ ] Alinear nombre de imagen Hub en todos lados: elegir **`zyrabitcore/zyrabit-slm`** *o* `zyrabit-platform` y unificar README / DOCKER_HUB / scripts de push
- [ ] Tabla de puertos: Lite = solo `8080`; `8088`/Grafana/etc. solo bajo “Platform / Compose”
- [ ] Marcar este archivo como **plan interno de rama** (evitar que un cold reader lo tome como onboarding)

#### Fase B — Defaults Lite
- [ ] Colapsar env requerido local a ~3–5: `INFERENCE_PROVIDER`, `SLM_URL`, (opcional) `MODEL_NAME`, API key
- [ ] Auto-generar `ZYRABIT_API_KEY_WEB` en primer boot y **imprimirla una vez** en logs/UI
- [ ] Documentar bridge `host.docker.internal` como default Mac/Win/Linux

#### Fase C — Compose Lite
- [ ] Añadir `docker-compose.dev.yml` (raíz o documentado) con api (+ web opcional) y Ollama en host
- [ ] Default source path no debe forzar 5 contenedores si existe imagen Hub all-in-one
- [ ] Profiles existentes (`monitoring`, `production`, `db`, `automation`, `bare`, Tenstorrent) se mantienen opt-in

#### Fase D — CLI delgado
- [ ] Superficie visible: `up` / `down` / `logs` / `doctor` (wrapper corto)
- [ ] Wizard → `zyra configure` (opcional); `install -y` sin prompts para CI
- [ ] No borrar capacidades enterprise; ocultarlas tras `help advanced`

#### Fase E — Makefile
- [ ] `make up` / `make down` / `make test` / `make doctor` apuntando al path Lite

#### Fase F — Valor de producto (UI backlog ya conocido)
- [ ] Sample PDF / “Try demo doc” en UI (&lt;2 min al primer wow)
- [ ] Split-screen evidence viewer (citas) — diferencial vs chat genérico
- [ ] Progress UI para pull de modelos Ollama
- [ ] Modal HITL para acciones MCP de escritura

### 5.5 Criterios de éxito

1. Usuario frío con Ollama: chat + RAG sin wizard ni Python/uv.
2. Un solo puerto mental en Lite: **8080**.
3. Contributor abre `CONTRIBUTING` y corre tests sin pasar por el wizard de 4 pasos.
4. Mensaje de marketing en una línea: *sovereign RAG with PII guardrails, one container*.

### 5.6 Fuera de alcance de este plan

- Reescribir la arquitectura hexagonal de `api-rag`
- Eliminar perfiles enterprise / Tenstorrent / n8n
- Implementar aquí las features UI (solo priorizarlas)
- Cambiar licencia o modelo de telemetría Scarf/cloud

### 5.7 Orden sugerido de ejecución

1. Cerrar Fase A (docs + naming) en esta rama / PR a `beta`
2. Fase B + C (env + compose lite) — mayor impacto DX
3. Fase D + E (CLI/Makefile) — higiene operador
4. Fase F en paralelo de producto
