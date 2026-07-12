#!/usr/bin/env bash
# validate-sdk-readiness.sh RUN_DIR [EXPECTED_RETRY_POLICY_YAML]
set -euo pipefail

RUN_DIR="${1:?run dir required}"
EXPECTED_POLICY="${2:-}"

fail() { echo "validate-sdk-readiness: $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$("$SCRIPT_DIR/bootstrap-python.sh")"

[[ -f "$RUN_DIR/schema/openapi.yaml" ]] || fail "missing schema/openapi.yaml"
[[ -f "$RUN_DIR/docs/sdk-readiness-report.md" ]] || fail "missing docs/sdk-readiness-report.md"

if [[ ! -f "$RUN_DIR/sdk/retry-policy.yaml" ]]; then
  echo "sdk_gate=NO-GO"
  exit 0
fi

if ! "$PYTHON" - <<'PY' "$RUN_DIR/sdk/retry-policy.yaml"
import sys
import yaml
from pathlib import Path

doc = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
ops = doc.get("operations") or {}
for op_id, entry in ops.items():
    if entry.get("policy") == "unreviewed":
        print(f"unreviewed:{op_id}")
        sys.exit(2)
    if not entry.get("confirmed"):
        print(f"unconfirmed:{op_id}")
        sys.exit(3)
print(f"operations={len(ops)}")
PY
then
  echo "sdk_gate=NO-GO"
  exit 0
fi

if [[ -n "$EXPECTED_POLICY" ]]; then
  if ! "$PYTHON" - <<'PY' "$RUN_DIR/sdk/retry-policy.yaml" "$EXPECTED_POLICY"
import sys
import yaml
from pathlib import Path

actual = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = yaml.safe_load(Path(sys.argv[2]).read_text(encoding="utf-8"))
for op_id, exp in (expected.get("operations") or {}).items():
    act = (actual.get("operations") or {}).get(op_id)
    if not act:
        raise SystemExit(f"missing operation {op_id}")
    if act.get("policy") != exp.get("policy"):
        raise SystemExit(f"policy mismatch {op_id}")
PY
  then
    echo "sdk_gate=NO-GO"
    exit 0
  fi
fi

for path in \
  "$RUN_DIR/generated/client.gen.go" \
  "$RUN_DIR/internal/transport/retry.go" \
  "$RUN_DIR/pkg/client/client.go" \
  "$RUN_DIR/scripts/regen.sh"; do
  [[ -f "$path" ]] || fail "missing deliverable $path"
done

echo "sdk_gate=GO"
