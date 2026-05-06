# ERP Integration

Zyrabit SLM can function as a local bridge for integrating enterprise ERP data with local AI capabilities.

## Integration Guidelines

- **Data Ingestion:** Push ERP data exports directly into Zyrabit ingestion jobs.
- **Secure Access:** Query the bridge via the secure `/v1/chat` endpoint.
- **Tool Exposure:** Expose curated ERP resources through the Model Context Protocol (`/mcp`).

Ensure that sensitive datasets remain within allowed MCP roots and that all outputs are sanitized by default to maintain data privacy.
