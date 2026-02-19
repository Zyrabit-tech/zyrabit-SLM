#!/usr/bin/env bash

set -euo pipefail

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

REPO_URL="${ZYRABIT_REPO_URL:-https://github.com/Zyrabit-tech/zyrabit-SLM.git}"

echo "Installing Zyrabit..."
git clone --depth 1 "${REPO_URL}" "${TMP_DIR}/zyrabit-SLM"
cd "${TMP_DIR}/zyrabit-SLM"
chmod +x "./zyra-up.sh"
./zyra-up.sh
