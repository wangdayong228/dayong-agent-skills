#!/usr/bin/env bash
# Validate openapi-from-sources output against expected-readiness.yaml markers.
# Usage:
#   validate-readiness-output.sh /path/to/run-dir /path/to/expected-readiness.yaml
set -euo pipefail

RUN_DIR="${1:?usage: validate-readiness-output.sh RUN_DIR EXPECTED_YAML}"
EXPECTED_YAML="${2:?usage: validate-readiness-output.sh RUN_DIR EXPECTED_YAML}"

if [[ ! -f "$EXPECTED_YAML" ]]; then
  echo "FAIL: expected file not found: $EXPECTED_YAML"
  exit 1
fi

failures=0
report_rel=$(awk -F': ' '/^report_path:/{print $2}' "$EXPECTED_YAML" | tr -d ' ')
report_path="$RUN_DIR/$report_rel"

yaml_list() {
  local key="$1"
  awk -v k="$key" '
    $0 ~ "^" k ":$" { in_list=1; next }
    in_list && /^[^[:space:]-]/ { exit }
    in_list && /^  - / {
      sub(/^  - /, "")
      if ($0 ~ /^".*"$/) { sub(/^"/, ""); sub(/"$/, "") }
      print
    }
  ' "$EXPECTED_YAML"
}

check_contains() {
  local file="$1"
  local label="$2"
  local list_key="$3"
  local needle
  while IFS= read -r needle; do
    [[ -z "$needle" ]] && continue
    if ! grep -Fq "$needle" "$file"; then
      echo "  - missing in $label: '$needle'"
      failures=$((failures + 1))
    fi
  done < <(yaml_list "$list_key")
}

check_not_contains() {
  local file="$1"
  local label="$2"
  local list_key="$3"
  local needle
  while IFS= read -r needle; do
    [[ -z "$needle" ]] && continue
    if grep -Fq "$needle" "$file"; then
      echo "  - forbidden in $label: '$needle'"
      failures=$((failures + 1))
    fi
  done < <(yaml_list "$list_key")
}

if [[ ! -f "$report_path" ]]; then
  echo "FAIL: validate-readiness-output"
  echo "  - missing report: $report_rel"
  exit 1
fi

check_contains "$report_path" "$report_rel" must_contain_in_report
check_not_contains "$report_path" "$report_rel" must_not_contain_in_report

while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  if [[ ! -f "$RUN_DIR/$rel" ]]; then
    echo "  - required output missing: $rel"
    failures=$((failures + 1))
  fi
done < <(yaml_list required_outputs)

while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  if [[ -f "$RUN_DIR/$rel" ]]; then
    echo "  - forbidden output exists: $rel"
    failures=$((failures + 1))
  fi
done < <(yaml_list forbidden_outputs)

openapi_path="$RUN_DIR/schema/openapi.yaml"
if [[ -f "$openapi_path" ]]; then
  check_contains "$openapi_path" "schema/openapi.yaml" must_contain_in_openapi
  check_not_contains "$openapi_path" "schema/openapi.yaml" must_not_contain_in_openapi
fi

if (( failures > 0 )); then
  echo "FAIL: validate-readiness-output"
  echo "  run_dir: $RUN_DIR"
  exit 1
fi

echo "PASS: validate-readiness-output"
echo "  run_dir: $RUN_DIR"
echo "  report: $report_rel"
