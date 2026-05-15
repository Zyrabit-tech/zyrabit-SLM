# 🛠️ Local Development Guide (No-Docker Mode)

To speed up development and avoid constant Docker rebuilds, you can run the API and Frontend natively on your machine while keeping only the database in Docker.

---

## 1. Prerequisites
- **Python 3.12+**
- **uv** (Python package manager)
- **Node.js 18+** (for the Frontend)
- **Docker** (only for the database)

---

## 2. Infrastructure Setup (Docker)
Keep the database running in the background.

```bash
# From the root directory
docker compose -f zyrabit-slm/docker-compose.local.yml up -d zyrabit-db
```

---

## 3. Backend Setup (Native)
Run the FastAPI server with **Hot Reload** enabled.

```bash
# 1. Enter the API directory
cd zyrabit-slm/api-rag

# 2. Sync dependencies (if not already done)
uv sync

# 3. Run the server
# The --reload flag ensures the server restarts on every file save
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

> [!TIP]
> Ensure your `.env` file in `zyrabit-slm/api-rag/` has `DB_URL=http://localhost:8000` to connect to the Dockerized DB from your host.

---

## 4. Frontend Setup (Native)
Run the Vite dev server for instant UI updates.

```bash
# 1. Enter the Web UI directory
cd zyrabit-slm/web-ui

# 2. Install dependencies
npm install

# 3. Run dev server
npm run dev
```

The UI will be available at `http://localhost:5173` (or the port Vite provides).

---

## 5. Development Workflow
1.  **Modify code** in `app/` or `src/`.
2.  **Save file** — the respective server will reload automatically.
3.  **Test in browser** — no Docker rebuild required!

---

## 7. Troubleshooting (Common Issues)

### ❌ `NameResolutionError: Failed to resolve 'host.docker.internal'`
**Cause:** You are running the API locally, but it's still trying to use the Docker-only bridge address.
**Fix:** In your `zyrabit-slm/api-rag/.env`, change `SLM_URL=http://host.docker.internal:11434` to `SLM_URL=http://localhost:11434`.

### ❌ `sqlite3.OperationalError: no such table: ingests`
**Cause:** The state tracking database was not initialized.
**Fix:** This is now handled automatically in `main.py`. Ensure you have the latest code where `IngestionTracker.init_db()` is called inside the `lifespan` function.
---

## 8. Monitoring & Observability

To see real-time metrics (latency, security hits, token usage), you can lift a simplified monitoring stack:

```bash
# From zyrabit-slm directory
docker compose -f docker-compose.monitoring.yml up -d
```

- **Grafana:** [http://localhost:3500](http://localhost:3500) (Auto-login as Admin)
- **Prometheus:** [http://localhost:9500](http://localhost:9500)

The pre-built dashboard **"Zyrabit SLM Command Center"** is automatically provisioned and connected to your local API.

### ❌ Frontend cannot connect to API (`404` or `CORS` error)
**Cause:** Vite is running on port 5173 and doesn't know where the API (port 8080) is.
**Fix:** Ensure you have `zyrabit-slm/web-ui/vite.config.js` with the `proxy` configuration pointing to `http://localhost:8080`.

### ❌ `ModuleNotFoundError: No module named 'app'`
**Cause:** Python doesn't see the `app` directory as a package.
**Fix:** Always run `uvicorn` from the `zyrabit-slm/api-rag` directory using:
`uv run uvicorn app.main:app --reload`
