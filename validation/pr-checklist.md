# Local PR Checklist (No Remote Push)

1. `uv run pytest -q` passes in `zyrabit-slm/api-rag`.
2. `./zyra-up.sh verify` passes on running stack.
3. MCP file read operations are strictly sandboxed and validated against absolute paths to prevent directory traversal attacks.
4. No secrets committed (`.env`, keys, tokens).
5. Validation artifacts reviewed:
   - `validation/k6/*.js`
   - `validation/pentest/checklist.md`
   - `validation/report-template.md`

