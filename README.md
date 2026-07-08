# dayong-agent-skills

Portable agent skills shared across coding agents.

This repository keeps reusable workflow skills in the open Agent Skills layout:
each skill is a directory under `skills/` with a `SKILL.md` file and optional
agent-specific metadata. The source of truth is the portable `SKILL.md`; any
agent-specific files are optional helpers, not the primary format.

## Included Skills

- `affected-path-review` - expands code review from changed lines to the full affected behavior path.
- `pr-comment-review` - fetches, evaluates, and addresses GitHub PR review feedback.
- `iterative-code-review` - runs a bounded subagent review loop where the main agent evaluates and fixes verified issues.

## Repository Layout

```text
skills/
  <skill-name>/
    SKILL.md
    agents/
      openai.yaml
```

`agents/openai.yaml` is optional Codex UI metadata. Other agents can ignore it
and read `SKILL.md` directly.

## Install For Codex

Codex discovers user skills from `~/.agents/skills`.

Use symlinks so local edits and `git pull` updates are immediately reflected:

```bash
repo="$HOME/myspace/mywork/dayong-agent-skills"
mkdir -p "$HOME/.agents/skills"

ln -sfn "$repo/skills/affected-path-review" "$HOME/.agents/skills/affected-path-review"
ln -sfn "$repo/skills/pr-comment-review" "$HOME/.agents/skills/pr-comment-review"
ln -sfn "$repo/skills/iterative-code-review" "$HOME/.agents/skills/iterative-code-review"
```

Restart Codex or force reload skills if a newly linked skill does not appear.

## Install For Claude Code

Claude Code commonly reads user skills from `~/.claude/skills`.

```bash
repo="$HOME/myspace/mywork/dayong-agent-skills"
mkdir -p "$HOME/.claude/skills"

ln -sfn "$repo/skills/affected-path-review" "$HOME/.claude/skills/affected-path-review"
ln -sfn "$repo/skills/pr-comment-review" "$HOME/.claude/skills/pr-comment-review"
ln -sfn "$repo/skills/iterative-code-review" "$HOME/.claude/skills/iterative-code-review"
```

Restart Claude Code or reload skills if needed.

## Use With Cursor

Cursor does not use the same skill discovery path as Codex or Claude Code.
Use this repository as the source text for Cursor rules:

1. Open the relevant `skills/<skill-name>/SKILL.md`.
2. Copy the reusable workflow instructions into a Cursor rule.
3. Keep the rule focused on the workflow and omit agent-specific metadata such as `agents/openai.yaml`.

If Cursor gains direct support for this skill layout later, keep `SKILL.md` as
the source of truth and add only the smallest required compatibility layer.

## Update

```bash
cd "$HOME/myspace/mywork/dayong-agent-skills"
git pull --ff-only
```

Symlink-based installs pick up updates from the repository automatically. If an
agent caches skill metadata, restart or reload skills after pulling.

## Authoring Rules

- Keep each skill focused on one job.
- Put reusable workflow instructions in `SKILL.md`.
- Keep `description` concise and trigger-oriented.
- Add scripts or references only when the workflow needs deterministic tooling or heavy reference material.
- Do not commit secrets, local logs, generated scratch files, or agent session transcripts.
