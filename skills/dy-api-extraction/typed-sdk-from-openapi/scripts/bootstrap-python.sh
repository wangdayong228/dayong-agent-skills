#!/usr/bin/env bash
# Ensure scripts/.venv with PyYAML; print python path.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [[ ! -x "$VENV/bin/python3" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q pyyaml
fi

echo "$VENV/bin/python3"
