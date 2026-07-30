---
name: codex-session-inspector
description: >-
  Use when checking local Codex session models, main-vs-subagent source,
  reasoning effort, token usage, or recent session details.
---

# Codex Session Inspector

Read-only Python CLI for local Codex session history.

| Command | Purpose |
| --- | --- |
| `list` | Recent sessions (model, source, cwd, title) |
| `tokens` | Token usage / context / rate-limit snapshots |
| `model` | Recent turn model + effort |
| `latest` | Newest session summary |
| `stats` | Model occurrence counts |

```bash
python3 scripts/inspect_sessions.py list
python3 scripts/inspect_sessions.py tokens --limit 20
python3 scripts/inspect_sessions.py model --limit 10
```

`--limit` applies to `list` / `tokens` / `model`. Defaults: list/tokens 20, model 50.

## Notes

- Reads `~/.codex/sessions/**/rollout-*.jsonl` (and `session_index.jsonl` for titles); never writes.
- Optional: `CODEX_HOME` overrides the Codex data root (default `~/.codex`).
