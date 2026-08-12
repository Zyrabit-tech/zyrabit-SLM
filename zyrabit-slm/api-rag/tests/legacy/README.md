# Legacy Test Suite

These tests are retained because they cover modules that still exist in the codebase, but they no longer serve as acceptance criteria for the document node. They cover MCP, ReAct, n8n, memory adapters, and the mock-based chat flow.

They are excluded from the main test suite execution. To reactivate them, set `ENABLE_LEGACY_EXTENSIONS=true` and update their contract expectations against current interfaces; running them without updating will produce false negatives.
