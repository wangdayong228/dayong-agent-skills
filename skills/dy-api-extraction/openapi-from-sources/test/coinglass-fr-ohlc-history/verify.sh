#!/usr/bin/env bash
# Offline checks for openapi-from-sources coinglass fixture expectations.
#
# Modes:
#   verify.sh
#     Skill structure + golden validator + generation test from fixture-input.
#   verify.sh /path/to/agent-run-dir
#     Above + validate agent output against expected-readiness.yaml.
set -euo pipefail

CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$CASE_DIR/../.." && pwd)"
RUN_DIR="${1:-}"
EXPECTED_YAML="$CASE_DIR/expected-readiness.yaml"
EXPECTED_FALLBACK_YAML="$CASE_DIR/expected-readiness-example-fallback.yaml"
GOLDEN_REPORT="$CASE_DIR/expected/openapi-readiness-report.md"
VALIDATOR="$SKILL_DIR/scripts/validate-readiness-output.sh"
GENERATOR="$SKILL_DIR/scripts/generate-openapi-from-sources.sh"

yaml_scalar() {
  local key="$1"
  awk -v k="$key" -F': ' '$1 == k { sub(/^[^:]*: */, ""); print; exit }' "$EXPECTED_YAML"
}

yaml_nested_markers() {
  awk '
    /^fixture_markers:/ { in_fm=1; next }
    in_fm && /^  fr_ohlc_histroy:/ { in_list=1; next }
    in_list && /^    - / {
      sub(/^    - /, "")
      if ($0 ~ /^".*"$/) { sub(/^"/, ""); sub(/"$/, "") }
      print
      next
    }
    in_list && /^  [a-z_]+:/ { exit }
    in_list && /^[^[:space:]]/ { exit }
  ' "$EXPECTED_YAML"
}

FIXTURE_ROOT="$CASE_DIR/$(yaml_scalar fixture_root)"
SIBLING_FIXTURE="$(cd "$SKILL_DIR/../strict-api-extraction/test/coinglass-fr-ohlc-history" 2>/dev/null && pwd || true)"

failures=0

check_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    echo "  - missing: $label"
    failures=$((failures + 1))
    return
  fi
  local size
  size=$(wc -c < "$path" | tr -d ' ')
  if (( size < 10 )); then
    echo "  - too small: $label"
    failures=$((failures + 1))
  fi
}

check_markers() {
  local file="$1"
  local label="$2"
  shift 2
  local needle
  for needle in "$@"; do
    if ! grep -Fq "$needle" "$file"; then
      echo "  - missing marker '$needle' in $label"
      failures=$((failures + 1))
    fi
  done
}

echo "== skill structure =="
check_file "$SKILL_DIR/SKILL.md" "SKILL.md"
check_file "$EXPECTED_YAML" "expected-readiness.yaml"
check_file "$EXPECTED_FALLBACK_YAML" "expected-readiness-example-fallback.yaml"
check_file "$GOLDEN_REPORT" "expected/openapi-readiness-report.md"
check_file "$VALIDATOR" "scripts/validate-readiness-output.sh"
check_file "$GENERATOR" "scripts/generate-openapi-from-sources.sh"
check_file "$SKILL_DIR/scripts/generate-openapi-from-sources.py" "scripts/generate-openapi-from-sources.py"

for script in "$VALIDATOR" "$GENERATOR"; do
  if [[ ! -x "$script" ]]; then
    echo "  - not executable: ${script#$SKILL_DIR/}"
    failures=$((failures + 1))
  fi
done

echo "== golden report validator =="
GOLDEN_TMP=$(mktemp -d)
mkdir -p "$GOLDEN_TMP/docs"
cp "$GOLDEN_REPORT" "$GOLDEN_TMP/docs/openapi-readiness-report.md"
if ! bash "$VALIDATOR" "$GOLDEN_TMP" "$EXPECTED_YAML"; then
  echo "  - golden report failed full validator"
  failures=$((failures + 1))
fi
rm -rf "$GOLDEN_TMP"

echo "== fixture-input =="
if [[ ! -d "$FIXTURE_ROOT/source/raw" ]]; then
  echo "  - missing committed fixture: $FIXTURE_ROOT/source/raw"
  failures=$((failures + 1))
else
  fr_file="$FIXTURE_ROOT/source/raw/fr-ohlc-histroy.md"
  check_file "$fr_file" "fixture-input fr-ohlc-histroy.md"
  markers=()
  while IFS= read -r m; do
    [[ -n "$m" ]] && markers+=("$m")
  done < <(yaml_nested_markers)
  if ((${#markers[@]} > 0)); then
    check_markers "$fr_file" "fixture-input fr-ohlc-histroy.md" "${markers[@]}"
  fi
fi

if [[ -n "$SIBLING_FIXTURE" && -d "$SIBLING_FIXTURE/source/raw" ]]; then
  echo "== sibling strict-api-extraction fixture (optional) =="
  check_markers "$SIBLING_FIXTURE/source/raw/fr-ohlc-histroy.md" "sibling fr-ohlc-histroy.md" \
    "/api/futures/funding-rate/history" "fr-ohlc-histroy"
fi

echo "== generation test (strict NO-GO from fixture-input) =="
GEN_TMP=$(mktemp -d)
if [[ -d "$FIXTURE_ROOT/source/raw" ]]; then
  gen_out=""
  if ! gen_out=$(bash "$GENERATOR" "$FIXTURE_ROOT" "$GEN_TMP" 2>&1); then
    echo "  - generator failed"
    echo "$gen_out"
    failures=$((failures + 1))
  elif [[ "$(printf '%s\n' "$gen_out" | awk -F= '/^schema_gate=/{print $2}')" != "NO-GO" ]]; then
    echo "  - expected schema_gate=NO-GO for coinglass strict fixture"
    echo "$gen_out"
    failures=$((failures + 1))
  elif ! bash "$VALIDATOR" "$GEN_TMP" "$EXPECTED_YAML"; then
    echo "  - generator output failed validator"
    failures=$((failures + 1))
  else
    echo "  $(printf '%s\n' "$gen_out" | grep '^schema_gate=')"
    echo "  generated readiness report from fixture-input (no schema/openapi.yaml)"
  fi
else
  echo "  SKIP: no fixture-input"
fi
rm -rf "$GEN_TMP"

echo "== generation test (example-fallback GO from fixture-input) =="
FALLBACK_TMP=$(mktemp -d)
if [[ -d "$FIXTURE_ROOT/source/raw" ]]; then
  fallback_out=""
  if ! fallback_out=$(bash "$GENERATOR" "$FIXTURE_ROOT" "$FALLBACK_TMP" --strictness example-fallback 2>&1); then
    echo "  - fallback generator failed"
    echo "$fallback_out"
    failures=$((failures + 1))
  elif [[ "$(printf '%s\n' "$fallback_out" | awk -F= '/^schema_gate=/{print $2}')" != "GO (example-fallback)" ]]; then
    echo "  - expected schema_gate=GO (example-fallback)"
    echo "$fallback_out"
    failures=$((failures + 1))
  elif ! bash "$VALIDATOR" "$FALLBACK_TMP" "$EXPECTED_FALLBACK_YAML"; then
    echo "  - fallback generator output failed validator"
    failures=$((failures + 1))
  else
    echo "  $(printf '%s\n' "$fallback_out" | grep '^schema_gate=')"
    echo "  generated schema/openapi.yaml with x-inferred-from: example"
  fi
else
  echo "  SKIP: no fixture-input"
fi
rm -rf "$FALLBACK_TMP"

echo "== strict rerun must not delete prior fallback openapi.yaml =="
REUSE_TMP=$(mktemp -d)
if [[ -d "$FIXTURE_ROOT/source/raw" ]]; then
  bash "$GENERATOR" "$FIXTURE_ROOT" "$REUSE_TMP" --strictness example-fallback >/dev/null
  if [[ ! -f "$REUSE_TMP/schema/openapi.yaml" ]]; then
    echo "  - fallback did not create schema/openapi.yaml"
    failures=$((failures + 1))
  elif ! bash "$GENERATOR" "$FIXTURE_ROOT" "$REUSE_TMP" >/dev/null 2>&1; then
    echo "  - strict rerun failed on reused output dir"
    failures=$((failures + 1))
  elif [[ ! -f "$REUSE_TMP/schema/openapi.yaml" ]]; then
    echo "  - strict rerun deleted prior schema/openapi.yaml"
    failures=$((failures + 1))
  else
    echo "  preserved schema/openapi.yaml after strict rerun"
  fi
fi
rm -rf "$REUSE_TMP"

if [[ -n "$RUN_DIR" ]]; then
  echo "== agent run output =="
  if [[ ! -d "$RUN_DIR" ]]; then
    echo "  - missing run dir: $RUN_DIR"
    failures=$((failures + 1))
  else
    bash "$VALIDATOR" "$RUN_DIR" "$EXPECTED_YAML"
  fi
fi

if (( failures > 0 )); then
  echo "FAIL: coinglass-fr-ohlc-history openapi-from-sources check"
  exit 1
fi

echo "PASS: coinglass-fr-ohlc-history openapi-from-sources check"
if [[ -n "$RUN_DIR" ]]; then
  echo "  validated run_dir: $RUN_DIR"
fi
