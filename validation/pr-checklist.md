# Local PR Checklist (No Remote Push)

1. `./.venv/bin/python -m pytest -q` passes in `zyrabit-brain-api/api-rag`.
2. `streamlit run slm_console.py` verifies:
   - chat works
   - upload + ingest works
   - route metadata is visible
3. `./scripts/run_final_tests.sh` passes on running stack.
4. No secrets committed (`.env`, keys, tokens).
5. Validation artifacts reviewed:
   - `validation/k6/*.js`
   - `validation/pentest/checklist.md`
   - `validation/report-template.md`

