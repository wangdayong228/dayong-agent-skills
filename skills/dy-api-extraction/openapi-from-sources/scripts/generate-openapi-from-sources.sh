#!/usr/bin/env bash
# Generate openapi-from-sources outputs from material root.
# Usage: generate-openapi-from-sources.sh MATERIAL_ROOT OUTPUT_DIR [--scope "..."] [--strictness strict|example-fallback]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATOR="$SCRIPT_DIR/generate-openapi-from-sources.py"

if [[ $# -lt 2 ]]; then
  echo "usage: generate-openapi-from-sources.sh MATERIAL_ROOT OUTPUT_DIR [--scope SCOPE]" >&2
  exit 1
fi

exec python3 "$GENERATOR" "$@"
