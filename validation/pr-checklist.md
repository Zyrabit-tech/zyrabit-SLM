# Local PR Checklist (No Remote Push)

1. `./.venv/bin/python -m pytest -q` passes in `zyrabit-slm/api-rag`.
2. `./zyrabit-slm/scripts/build_and_verify.sh` passes on running stack.
4. No secrets committed (`.env`, keys, tokens).
5. Validation artifacts reviewed:
   - `validation/k6/*.js`
   - `validation/pentest/checklist.md`
   - `validation/report-template.md`

