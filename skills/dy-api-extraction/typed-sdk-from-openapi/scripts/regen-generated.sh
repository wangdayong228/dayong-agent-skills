#!/usr/bin/env bash
# regen-generated.sh [RUN_DIR]
set -euo pipefail

RUN_DIR="${1:-.}"
SPEC="$RUN_DIR/schema/openapi.yaml"
OUT="$RUN_DIR/generated/client.gen.go"

if [[ ! -f "$SPEC" ]]; then
  echo "regen-generated: missing $SPEC" >&2
  exit 1
fi

mkdir -p "$RUN_DIR/generated"
oapi-codegen -generate types,client -package generated -o "$OUT" "$SPEC"
echo "generated=$OUT"
