#!/usr/bin/env bash

set -euo pipefail

SESSION_DIR="${HOME}/.codex/sessions"

if [ ! -d "$SESSION_DIR" ]; then
    echo "Codex session directory not found: $SESSION_DIR"
    exit 1
fi

latest_file() {
    find "$SESSION_DIR" -type f -name "*.jsonl" -print0 | xargs -0 ls -t | head -n1
}

case "${1:-model}" in
model)
    printf "%-20s %-12s %-25s %-10s\n" TIME SOURCE MODEL EFFORT
    find "$SESSION_DIR" -type f -name "*.jsonl" -print0 |
    xargs -0 -I{} jq -r '
        select(.type=="turn_context") |
        [(.timestamp // ""), (.payload.source // "main"), (.payload.model // ""), (.payload.effort // .payload.reasoning_effort // "")] | @tsv
    ' {} |
    tail -50 |
    while IFS=$'\t' read -r t s m e; do
        printf "%-20s %-12s %-25s %-10s\n" "$t" "$s" "$m" "$e"
    done
    ;;
latest)
    f=$(latest_file)
    echo "FILE:"
    echo "$f"
    jq 'select(.type=="session_meta") | .payload' "$f"
    ;;
stats)
    find "$SESSION_DIR" -type f -name "*.jsonl" -print0 |
    xargs -0 jq -r 'select(.type=="turn_context") | .payload.model' |
    sort | uniq -c | sort -nr
    ;;
*)
    echo "Usage: $0 {model|latest|stats}"
    exit 1
    ;;
esac
