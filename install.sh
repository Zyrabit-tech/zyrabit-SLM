#!/usr/bin/env bash

set -euo pipefail

REPO_URL="${ZYRABIT_REPO_URL:-https://github.com/Zyrabit-tech/zyrabit-SLM.git}"
INSTALL_DIR="${ZYRABIT_INSTALL_DIR:-$HOME/.zyrabit}"

echo "============================================================"
echo "          🐝 Installing Zyrabit Platform                    "
echo "============================================================"

if [ -d "${INSTALL_DIR}/.git" ]; then
    echo "Updating existing installation at ${INSTALL_DIR}..."
    cd "${INSTALL_DIR}"
    git pull origin main 2>/dev/null || git pull origin beta 2>/dev/null || true
else
    echo "Cloning Zyrabit Platform into ${INSTALL_DIR}..."
    mkdir -p "$(dirname "${INSTALL_DIR}")"
    git clone --depth 1 "${REPO_URL}" "${INSTALL_DIR}"
    cd "${INSTALL_DIR}"
fi

chmod +x "./zyra.sh" "./zyra-up.sh"

# Offer or configure symlink if directory is available
BIN_DIR=""
if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]] && [ -d "$HOME/.local/bin" ]; then
    BIN_DIR="$HOME/.local/bin"
elif [[ -w "/usr/local/bin" ]]; then
    BIN_DIR="/usr/local/bin"
elif [ -d "$HOME/.local/bin" ]; then
    BIN_DIR="$HOME/.local/bin"
fi

if [ -n "${BIN_DIR}" ]; then
    ln -sf "${INSTALL_DIR}/zyra.sh" "${BIN_DIR}/zyra"
    echo "✔ Linked 'zyra' CLI to ${BIN_DIR}/zyra"
fi

echo "✔ Zyrabit Platform installed in ${INSTALL_DIR}"
./zyra.sh "${@:-install}"

