# Caso 3 — Agente ops gobernado (HITL + webhook allowlisted)

Demo **replicable** del flujo:

`intent → policy → HITL → tool allowlisted → audit`

Alineado con [`docs/engineering/AGENT_TOOL_RUNTIME_MAP.md`](../../docs/engineering/AGENT_TOOL_RUNTIME_MAP.md).

> **Nota:** el MCP actual del repo (`mcp/`) solo expone tools de diagnóstico. Este ejemplo modela el **caso 3** (crear ticket) con un inbox HTTP local que simula Jira/Linear/n8n, para que cualquiera lo corra sin credenciales cloud.

## Qué demuestra

| Escenario | Resultado |
|---|---|
| `ticket.create` en perfil `ops` | Policy = `ask_human` → apruebas → ticket en inbox |
| `nmap.scan` (ejemplo inseguro) | Policy = `deny` → sin side effects |
| HITL reject (`--approve no`) | No se crea ticket |

## Requisitos

- Python 3.10+ (stdlib only; PyYAML opcional)
- Dos terminales (o un server en background)

## Cómo montarlo (5 minutos)

```bash
# desde la raíz del repo
cd examples/case3-hitl-ops

# 1) Inbox mock (simula Jira/Linear)
python3 scripts/mock_ticket_server.py
# → http://127.0.0.1:8765
```

En otra terminal:

```bash
cd examples/case3-hitl-ops

# 2) Happy path — crear ticket con HITL aprobado
python3 scripts/run_case3.py \
  --profile ops \
  --approve yes \
  --title "Fallo de login en prod" \
  --priority high \
  --requester abraham

# 3) Deny — tool no permitido
python3 scripts/run_case3.py --profile ops --deny-tool nmap.scan

# 4) HITL rechazado — sin side effects
python3 scripts/run_case3.py --profile ops --approve no --title "No debe crearse"
```

## Salidas

| Archivo | Contenido |
|---|---|
| `out/tickets.jsonl` | Tickets creados en el inbox mock |
| `out/audit.jsonl` | Ledger: proposed → hitl → success/deny |
| `data/sample-run/` | Captura de una corrida real de referencia |

Ejemplo de ticket (sample-run):

```json
{
  "id": "TCK-7E975591",
  "title": "Fallo de login en prod",
  "priority": "high",
  "requester": "abraham",
  "source": "zyrabit-case3-demo"
}
```

## Policy

Ver `policy.yml` / `policy.json`:

- perfil `safe`: solo reads
- perfil `ops`: writes/external → `ask_human`
- tools ofensivos de ejemplo → `deny`

## Cómo llevarlo a producción (Zyrabit Platform)

1. Sustituir el mock por un webhook real allowlisted (Jira / Linear / n8n).
2. Meter la misma policy en el runtime del agente (MCP whitelist + HITL UI).
3. Mantener Lite en `:8080` para chat/RAG; perfil `ops` solo para acciones.
4. Nunca dejar que el LLM registre tools arbitrarios sin firma humana.

## Post largo (Medium)

Borrador listo para publicar: [`docs/medium/caso-3-agente-ops-gobernado.md`](../../docs/medium/caso-3-agente-ops-gobernado.md)
