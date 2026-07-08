#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"

cd "${SCRIPT_DIR}"

if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
    echo "Error: virtual environment not found. Run ./setup_pi.sh first." >&2
    exit 1
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

if [[ -f "${SCRIPT_DIR}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.env"
    set +a
fi

exec python -m pi_client.main

