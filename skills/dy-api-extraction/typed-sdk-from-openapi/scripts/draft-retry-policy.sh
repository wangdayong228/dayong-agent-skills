#!/usr/bin/env bash
# Draft retry-policy.yaml from OpenAPI spec (bootstraps PyYAML venv).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$("$SCRIPT_DIR/bootstrap-python.sh")"
exec "$PYTHON" "$SCRIPT_DIR/draft_retry_policy.py" "$@"
