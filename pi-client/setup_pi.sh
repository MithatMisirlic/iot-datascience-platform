#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "${SCRIPT_DIR}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "Error: ${PYTHON_BIN} is not installed or not available on PATH." >&2
    exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
    echo "Creating virtual environment at ${VENV_DIR}..."
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "Installing Raspberry Pi client dependencies..."
python -m pip install --upgrade pip
python -m pip install --requirement "${SCRIPT_DIR}/requirements.txt"

mkdir -p "${SCRIPT_DIR}/recordings"

if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
    cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
    echo "Created .env from .env.example."
else
    echo "Keeping existing .env file."
fi

chmod +x "${SCRIPT_DIR}/run_pi.sh"

cat <<EOF

Pi client setup complete.

Next steps:
  1. Review ${SCRIPT_DIR}/.env and configure the WebSocket server and hardware flags.
  2. Start the client with: ${SCRIPT_DIR}/run_pi.sh
  3. Use PI_MOCK_MODE=true in .env when testing without connected sensors.
EOF

