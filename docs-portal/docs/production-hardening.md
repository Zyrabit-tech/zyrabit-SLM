# Production Hardening Checklist

Transitioning from a development environment to a production deployment requires strict adherence to security and resource management policies. Use this checklist to ensure your Zyrabit SLM instance is hardened for production.

## 1. Network Security & TLS

Zyrabit should never be exposed directly to the public internet. Always use a reverse proxy for TLS termination and header sanitization.

- [ ] **TLS Termination:** Use Traefik, Nginx, or Caddy to handle HTTPS (Port 443).
- [ ] **Strict Entrypoints:** Disable access to Port 80. Redirect all traffic to 443.
- [ ] **IP Whitelisting:** If possible, restrict API access to specific internal IP ranges.

### Example Traefik Configuration (Label-based)
```yaml
labels:
  - "traefik.http.routers.zyrabit.rule=Host(`zyra.company.com`)"
  - "traefik.http.routers.zyrabit.entrypoints=websecure"
  - "traefik.http.routers.zyrabit.tls.certresolver=myresolver"
```

## 2. Authentication & Authorization

Ensure that every request to the Zyrabit API is authenticated.

- [ ] **Service Tokens:** Generate unique tokens for each consuming service.
- [ ] **HMAC Validation:** For webhook-based integrations (e.g., n8n), enable HMAC signature verification in the adapter.
- [ ] **Secrets Management:** Use Docker Secrets or an external Vault. Never hardcode tokens in `docker-compose.yaml`.

## 3. Resource Constraints (cgroups)

Prevent the AI inference engine from starving other critical system services of CPU or RAM.

- [ ] **RAM Limits:** Set a hard limit slightly above your *Hardware Tier* requirement.
- [ ] **Reserved Memory:** Ensure enough memory is reserved for the host OS to prevent OOM (Out Of Memory) kills.

```yaml
services:
  zyrabit-engine:
    deploy:
      resources:
        limits:
          memory: 16G
        reservations:
          memory: 8G
```

## 4. Observability & Auditing

- [ ] **PII Redaction:** Ensure logs do not contain personally identifiable information (PII).
- [ ] **Retention Policies:** Configure Prometheus and log rotation to prevent disk exhaustion.
- [ ] **Alerting:** Set up alerts for high inference latency (>10s) or service downtime.

## 5. Storage Durability

- [ ] **Persistent Volumes:** Verify that all `./data` directories are mapped to persistent, backed-up storage.
- [ ] **Snapshot Schedule:** Implement a daily snapshot policy for the vector database (`./data/vector-db`).
