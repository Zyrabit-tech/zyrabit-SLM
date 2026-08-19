#!/usr/bin/env bash
# Real-node acceptance check. It never creates a fixture or substitutes a model.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/zyrabit-slm/.env"
PDF_PATH="${ZYRABIT_SMOKE_PDF:-${ROOT_DIR}/zyrabit-slm/api-rag/docs/zyrabit-cioreview-en.pdf}"
API_URL="${ZYRABIT_SMOKE_API_URL:-http://localhost:8080/v1}"

[[ -f "${PDF_PATH}" ]] || { echo "Acceptance PDF not found: ${PDF_PATH}" >&2; exit 1; }
[[ -f "${ENV_FILE}" ]] || { echo "Missing ${ENV_FILE}; run ./zyra.sh install first." >&2; exit 1; }

API_KEY="$(grep '^ZYRABIT_API_KEY_WEB=' "${ENV_FILE}" | cut -d= -f2-)"
[[ -n "${API_KEY}" ]] || { echo "ZYRABIT_API_KEY_WEB is not configured." >&2; exit 1; }

tmp_json="$(mktemp -t zyrabit-node-smoke.XXXXXX)"
trap 'rm -f "${tmp_json}"' EXIT

curl --fail --silent --show-error -X POST "${API_URL}/sources/import" \
  -H "Authorization: Bearer ${API_KEY}" \
  -F "file=@${PDF_PATH};type=application/pdf" > "${tmp_json}"

read -r job_id document_id < <(python3 - "${tmp_json}" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
print(payload.get("job_id", ""), payload.get("document_id", ""))
PY
)
[[ -n "${document_id}" ]] || { echo "Import did not return document_id: $(cat "${tmp_json}")" >&2; exit 1; }

if [[ -n "${job_id}" ]]; then
  for _ in $(seq 1 120); do
    curl --fail --silent --show-error -H "Authorization: Bearer ${API_KEY}" "${API_URL}/jobs/${job_id}" > "${tmp_json}"
    state="$(python3 - "${tmp_json}" <<'PY'
import json, sys
print(json.load(open(sys.argv[1])).get("status", ""))
PY
)"
    [[ "${state}" == "ready" ]] && break
    [[ "${state}" == "failed" ]] && { echo "Indexing failed: $(cat "${tmp_json}")" >&2; exit 1; }
    sleep 1
  done
  [[ "${state}" == "ready" ]] || { echo "Indexing timed out." >&2; exit 1; }
fi

curl --fail --silent --show-error -X POST "${API_URL}/query" \
  -H "Authorization: Bearer ${API_KEY}" -H 'Content-Type: application/json' \
  -d "{\"text\":\"What operation is crucial for regulated environments?\",\"session_id\":\"real-node-smoke\",\"document_id\":\"${document_id}\"}" > "${tmp_json}"

python3 - "${tmp_json}" "${document_id}" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
sources = payload.get("metadata", {}).get("sources", [])
if not sources or any(source.get("document_id") != sys.argv[2] for source in sources):
    raise SystemExit(f"Response lacks evidence from the imported document: {payload}")
if not any(source.get("locator", {}).get("page") for source in sources):
    raise SystemExit(f"Response lacks a stable page locator: {payload}")
print("PASS: imported PDF, indexed it, queried it, and received scoped page evidence.")
PY
