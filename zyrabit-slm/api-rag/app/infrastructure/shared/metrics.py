from prometheus_client import Counter, Histogram

# --- Zyrabit Prometheus Metrics ---
# Centralized registry for application-specific metrics.

# Token Usage (Prompt + Completion)
TOKEN_USAGE_TOTAL = Counter(
    "zyrabit_token_usage_total",
    "Total tokens consumed by SLM",
    ["model", "direction"] # direction: input, output
)

# Latency Tracking
TOKEN_LATENCY_MS = Histogram(
    "zyrabit_token_latency_ms",
    "End-to-end inference latency in milliseconds",
    ["model"]
)

# Security & PII Gatekeeper Hits
SECURITY_HITS_TOTAL = Counter(
    "zyrabit_security_hits_total",
    "Total number of PII or out-of-scope interceptions",
    ["entity_type", "action"] # action: masked, rejected
)

# RAG Performance
RAG_HITS_TOTAL = Counter(
    "zyrabit_rag_hits_total",
    "Total number of vector database retrievals",
    ["collection"]
)
