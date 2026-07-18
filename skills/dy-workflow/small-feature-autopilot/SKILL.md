---
name: small-feature-autopilot
description: >-
  Use when the user asks to auto-complete a small, low-risk feature without
  mid-process confirmation — e.g. "自动到底", "小功能", "无需确认", or explicit
  invocation of this skill. Do not use for multi-subsystem, architectural,
  breaking, or high-stakes work.
---

# Small Feature Autopilot

Same superpowers artifacts/skills; **confirmation gates removed**.

**Announce:** "Using small-feature-autopilot to execute this end-to-end."

## When To Use

ALL of: single subsystem / few related files; no expected API/schema/behavior breaks; not high-stakes (money, security, permissions, irreversible data); user wants autopilot.

Otherwise: full superpowers (`brainstorming` → approval → `writing-plans` → execution).

## Workflow

```
S0 Gate → S1 Spec → S2 Plan → S3 Execute → S4 Verify → S5 Report
```

No mid-step confirmation. Pause only on Stop Conditions.

### S0 — Complexity Gate

Before any artifact. Any signal → warn and stop:

| Signal | Threshold |
|--------|-----------|
| Subsystems | > 1 independent |
| Files | > ~8 created/modified |
| Plan tasks | > ~5 bite-sized |
| Design ambiguity | Multiple valid architectures with real trade-offs |
| Breaking change | Public API / schema / behavior incompatibility |
| High-stakes | Money, security, permissions, irreversible data |

```markdown
## ⚠️ 需求规模超出 Autopilot 适用范围

此需求涉及 [具体原因]，不适合 small-feature-autopilot。
建议：`brainstorming` → spec 审阅 → `writing-plans` → 分步执行
是否切换到完整流程？
```

### S1 — Minimal Spec (saved, no approval)

`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`:

```markdown
# [Feature] — Minimal Spec
> Autopilot mode. No user approval gate.
## Goal
[one sentence]
## Scope
- [files/areas]
## Out of Scope
- [what NOT to change]
## Acceptance Criteria
- [ ] [criterion]
## Verify
- `[exact command]`
## Key Decisions
- [brief, if any]
```

Self-review before save. Direction-changing ambiguity → hard blocker. Chat summary ≤8 lines → S2.

### S2 — Plan (saved, no approval)

`writing-plans` → `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`. Auto-pick `subagent-driven-development` if available, else `executing-plans`. No execution-option prompt → S3.

### S3 — Execute

Follow chosen skill exactly. No continue prompts. Minimal diff; no commit unless asked. Then `finishing-a-development-branch` (pause only if it needs a merge/PR decision).

### S4 — Verify

1. `pre-verification-check`
2. `verification-before-completion` (spec Verify commands)
3. Fail → fix → re-run (max **2** rounds); still failing → hard blocker
4. `consistency-check` vs acceptance criteria

### S5 — Report

```markdown
## Autopilot Report
### Artifacts
- Spec / Plan paths
### Changes
- `path` — [why]
### Key Decisions
- [or none]
### Verification
- Command / Result (pass/fail + evidence)
### Remaining Risks / Follow-ups
- [or none]
```

## Stop Conditions

| Condition | Example |
|-----------|---------|
| Complexity gate | Multi-subsystem / too many files |
| Requirement conflict | Two interpretations, different behavior |
| Missing critical info | Unknown rule / dependency |
| Breaking change detected | Public API or response shape change |
| High-stakes domain | Auth, payments, secrets, irreversible writes |
| Auto-fix exhausted | 2 fix rounds still failing |
| Scope creep | Grew beyond small-feature mid-run |

When pausing: what blocked, what you tried, what decision you need.

## Example

> …加 WithTimeout，自动做到底 → S0 pass → S1–S5.  
> …重构 transport 拆 5 包，自动做到底 → S0 fail; do **not** start S1.
