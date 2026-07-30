---
name: codex-session-inspector
description: Use when checking local Codex session models, main-vs-subagent source, reasoning effort, token usage, or recent session details.
---

# Codex Session Inspector

Inspect local Codex session history with a Python standard-library CLI.

Use this skill when user wants to know:
- Which LLM model Codex recently used
- Main agent vs subagent model
- Reasoning effort level
- Recent session information
- Codex model occurrence statistics
- Token usage

## Commands

### Recent model

```bash
python3 scripts/inspect_sessions.py model --limit 10
```

### Latest session

```bash
python3 scripts/inspect_sessions.py latest
```

### Statistics

```bash
python3 scripts/inspect_sessions.py stats
```

### Token usage

```bash
python3 scripts/inspect_sessions.py tokens --limit 20
```

### Recent sessions

```bash
python3 scripts/inspect_sessions.py list
```

## Notes

- Sessions are stored in nested paths such as `~/.codex/sessions/**/rollout-*.jsonl`.
- Session titles are read from `~/.codex/session_index.jsonl` for `list`.
- The CLI is read-only: it does not modify Codex configuration or session data.
- Set `CODEX_HOME` to inspect another Codex data directory; it defaults to `~/.codex`.
