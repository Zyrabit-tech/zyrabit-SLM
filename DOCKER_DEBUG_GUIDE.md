# 🐳 Docker Management & Debugging Guide

This guide provides explicit instructions on how to manage, build, and debug the Zyrabit SLM containerized stack.

---

## 🛠️ Building and Rebuilding

### Build the entire stack
To rebuild all images from scratch (ignoring cache if needed):
```bash
docker compose -f zyrabit-slm/docker-compose.local.yml build --no-cache
```

### Rebuild a specific service
If you only modified the API or the Web UI, you can rebuild just that container:
```bash
# Rebuild only the API
docker compose -f zyrabit-slm/docker-compose.local.yml up -d --build zyrabit-api

# Rebuild only the Web UI
docker compose -f zyrabit-slm/docker-compose.local.yml up -d --build zyrabit-web
```

---

## 🔍 Debugging Commands

### View Logs
The first step in any debug session:
```bash
# Continuous logs for the API
docker logs -f zyrabit-api

# Last 50 lines of all services
docker compose -f zyrabit-slm/docker-compose.local.yml logs --tail 50
```

### Inspect Container State
Check environment variables, network settings, and mounts:
```bash
docker inspect zyrabit-api
```

### Shell Access
Enter a running container to explore the filesystem or run manual scripts:
```bash
docker exec -it zyrabit-api /bin/bash
```

---

## 🏗️ Understanding `zyra-up.sh` & Profiles

The `zyra-up.sh` script is a wrapper around `docker compose` that handles hardware detection and profile management.

### How it works:
1.  **Detection:** It checks if you are on a Mac (Apple Silicon), Linux with NVIDIA, or a low-resource machine.
2.  **Profile Selection:** Based on the detection, it applies specific Docker Compose profiles.
3.  **Execution:** It runs `docker compose --profile <name> up -d`.

### Available Profiles:
| Profile | Description |
|---|---|
| `n8n` | Adds the n8n automation engine to the stack. |
| `observability-extra` | Adds Loki and advanced log scraping. |
| `metal` | *(Auto-detected)* Optimizes for Apple Silicon. |
| `cuda` | *(Auto-detected)* Optimizes for NVIDIA GPUs. |

---

## ➕ Adding or Modifying Profiles

Profiles are defined directly in the `docker-compose.yml` (or `docker-compose.local.yml`) files using the `profiles` key.

### To add a new profile:
1.  Open `zyrabit-slm/docker-compose.local.yml`.
2.  Define your service and add the `profiles` property:
    ```yaml
    services:
      my-new-tool:
        image: custom-tool:latest
        profiles: ["my-profile"] # This service only starts with this profile
        networks:
          - backend-network
    ```
3.  Run it using the CLI:
    ```bash
    ./zyra-up.sh start --profile my-profile
    ```

### To modify `zyra-up.sh` logic:
If you want to add a new hardware-based auto-profile, search for the `detect_hardware` function in `zyra-up.sh` and add your logic there.

---

## 🚀 Pro-Tips for Developers

- **Clean start:** If things get messy, use `docker system prune -f` to clean up unused layers and containers.
- **Port Conflicts:** If port 80 or 443 is busy, use the `--local` flag in `zyra-up.sh` to run the API directly on port 8080.
- **Dependency Sync:** Remember that `zyrabit-api` uses the root `pyproject.toml`. If you add a library, you **must** rebuild the image.
