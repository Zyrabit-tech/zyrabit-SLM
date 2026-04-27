from prometheus_client import Counter, Histogram

# KISS Telemetry Metrics
# Following clean architecture, this centralizes our business metrics without
# adding the heavy overhead of OpenTelemetry.

zyrabit_token_usage_total = Counter(
    "zyrabit_token_usage_total",
    "Total tokens consumed by SLM (prompt and completion)",
    ["model", "provider"]
)

zyrabit_token_latency_ms_per_token = Histogram(
    "zyrabit_token_latency_ms_per_token",
    "Latency per token generated in milliseconds",
    ["model", "provider"]
)

zyrabit_security_hits_total = Counter(
    "zyrabit_security_hits_total",
    "Total number of security or PII interceptions",
    ["entity_type", "action"]
)
