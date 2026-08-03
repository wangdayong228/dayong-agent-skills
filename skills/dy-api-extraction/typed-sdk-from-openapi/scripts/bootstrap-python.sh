#!/usr/bin/env bash
# Find an existing Python with PyYAML; never install dependencies.
set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
  candidate="$(command -v python3)"
  if "$candidate" -c 'import yaml' >/dev/null 2>&1; then
    echo "$candidate"
    exit 0
  fi
fi

echo "bootstrap-python: PyYAML is required; install it for an existing python3 interpreter" >&2
exit 1
