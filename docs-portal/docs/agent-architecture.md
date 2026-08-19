# AI Agent Management & Orchestration Architecture

Zyrabit SLM manages AI Agents using a deterministic, sovereign **ReAct (Reasoning + Acting) Harness** paired with a zero-overhead **Intent Classifier**, **PII Protection Sandwich**, and **Model Context Protocol (MCP)** tool execution bridge.

---

## 1. Agent Execution Lifecycle

When a user query arrives at `/v1/chat` or via Socket.IO / Telegram / n8n, the agent harness processes the request through five distinct stages:

```
[ User Request ]
       │
       ▼
 1. Intent Classifier (0ms) ──► Loads ONLY relevant tools (Lazy Tool Loading)
       │
       ▼
 2. PII Masking Shield ───────► Anonymizes sensitive entities in prompt
       │
       ▼
 3. Token Budget Validator ───► Verifies context size < 70% of LLM window
       │
       ▼
 4. ReAct Reasoning Loop ─────► Iterates: Thought ➔ Action ➔ Observation
       │                              │
       │                              ▼ (Restore PII for Tool Args ➔ Execute ➔ Re-mask Output)
       ▼
 5. Final Answer / State Log ─► De-anonymizes response ➔ Persists to SQLite WAL
```

---

## 2. Core Subsystems

### A. Lazy Tool Loading (`classify_intent`)
Traditional AI agent frameworks inject every tool schema into the system prompt. For 50+ enterprise tools, this burns thousands of tokens and degrades SLM reasoning accuracy.

Zyrabit SLM solves this with a **deterministic, 0ms intent classifier** (`app/domain/agent/react_harness.py`):

- **Keyword Matching**: Scans query for intent groups (`radar`, `telegram`, `vault`, `docker`, `obsidian`, `diagnostic`, `docs`).
- **Dynamic Tool Schema Ingestion**: Supplies *only* the tool subset relevant to the current iteration.
- **Token Savings**: Reduces system prompt tool footprint by **80%+**.

### B. PII Sandwich Protocol
To maintain strict data sovereignty, sensitive data is protected at every boundary:

1. **Input Anonymization**: Gatekeeper replaces PII (names, SSNs, credit cards, IPs) with token placeholders (e.g. `[PER_1]`, `[IP_1]`).
2. **Tool Parameter De-anonymization**: Before invoking external tools (e.g. Docker, SQLite, local files), parameters are recursively restored to real values (`restore_pii_recursive`).
3. **Output Re-anonymization**: Tool results are re-masked before being fed back into the LLM observation window.

### C. Token Budget Validator & Emergency Compactor
SLMs perform best when context remains within optimal attention bounds. The harness enforces:

- **70% Window Cap**: Calculates combined token budget across system prompt, sliding window history (max 3 turns), and RAG retrieved context.
- **Emergency Compaction**: If context exceeds limits, the harness automatically drops low-priority RAG context and trims chat history to prevent context truncation.

### D. Model Context Protocol (MCP) RPC Bridge
Zyrabit SLM exposes all registered tools over standard **Model Context Protocol (MCP RPC 2.0)**:

- **Discovery (`/mcp/tools`)**: Exposes schemas for connected clients.
- **Execution (`/mcp/rpc`)**: Safe RPC execution of tool calls (e.g. `tools/call`) with strict argument schema validation and audit logging.

---

## 3. Configuration & Operational Commands

AI Agent management and extensions can be toggled via environment configuration:

```env
# Enable legacy extensions (ReAct harness, MCP, Telegram bridge)
ENABLE_LEGACY_EXTENSIONS=true

# Set max ReAct reasoning iterations (default: 5)
AGENT_MAX_ITERATIONS=5

# MCP tool whitelist configuration
MCP_WHITELIST_FILE=mcp/mcp-tools-whitelist.yml
```

### Running Agent Unit & Integration Tests

```bash
# Run node agent harness pytest suite
PYTHONPATH=zyrabit-slm/api-rag .venv/bin/python -m pytest zyrabit-slm/api-rag/tests/node/
```
