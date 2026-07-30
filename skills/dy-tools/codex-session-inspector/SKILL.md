# Codex Session Inspector

## Purpose

Inspect local Codex session history.

Use this skill when user wants to know:
- Which LLM model Codex recently used
- Main agent vs subagent model
- Reasoning effort level
- Recent session information
- Codex usage statistics

## Commands

### Recent model

```bash
bash scripts/inspect_sessions.sh model
```

### Latest session

```bash
bash scripts/inspect_sessions.sh latest
```

### Statistics

```bash
bash scripts/inspect_sessions.sh stats
```

## Notes

This skill reads:

~/.codex/sessions/*.jsonl

It does not modify Codex configuration.
