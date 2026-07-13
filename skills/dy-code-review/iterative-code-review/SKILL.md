---
name: iterative-code-review
description: Use when the user asks Codex to have a subagent, reviewer agent, or AI reviewer inspect local code changes and then have the main agent evaluate and fix issues until the code is clean.
---

# Iterative Code Review

## Overview

Run a bounded review loop: the main agent and readonly review subagent(s) inspect the current code in parallel, the main agent merges and adjudicates every finding, fixes only verified issues, then repeats until there are no actionable findings or three review rounds have completed.

The main agent remains accountable. Subagent feedback is evidence to evaluate, not instructions to obey.

**Core principles:**

- **Context-first:** Subagents never inherit the main agent's session history. Before each review round, the main agent snapshots scope, diff, affected behavior, and prior-round raw facts into one **Review Context Pack** reused for all subagents in that round.
- **Parallel review:** Each round, the main agent reviews code **in the same turn** as subagent dispatch—read files, trace paths, record findings while subagent(s) run. Do not wait for subagent results before starting review.
- **Default one subagent:** Dispatch **one** cost-effective readonly review subagent unless the user explicitly asks for multiple subagents (e.g. "多个子代理", "多模型 review", "multi-reviewer").
- **Same-LLM skip:** Do **not** dispatch a subagent when it would use the **same LLM** as the main agent (same `model` identifier or equivalent backend). In that case, the main agent's parallel review is sufficient for that round—no redundant same-model subagent.
- **Role split:** Subagents review only (`readonly: true`). The main agent owns adjudication, fixes, and verification. Use implementation-grade models for fixes if needed; do not use them for review passes.

## Required Sub-Skills

Before editing code, load the environment's relevant skills by capability:

- `affected-path-review` when correctness may depend on code beyond changed lines.
- `review-bugbot` on Cursor for the default review subagent.
- `review-security` on Cursor when multi-subagent mode is active and changes touch security boundaries.
- `dispatching-parallel-agents` for parallel main-agent review and subagent dispatch.
- External-review evaluation capability before accepting or rejecting findings.
- Debugging/root-cause capability for bugs or surprising behavior.
- Test-first capability before behavior changes.
- High-stakes implementation/testing capability for money, security, permissions, data loss, contracts, transactions, migrations, or irreversible actions.
- Verification and consistency capability before claiming completion.

If the request is about GitHub PR comments or review threads, use `pr-comment-review` first, then use this skill only for the local review loop.

## Loop Contract

Run at most three rounds. Track this state explicitly:

| Field | Meaning |
| --- | --- |
| `round` | 1, 2, or 3 |
| `review_scope` | Files, diff, PR, or command output reviewed |
| `main_agent_findings` | Findings from the main agent's parallel review (`source: main-agent`) |
| `subagents` | Subagents dispatched this round (type + model); empty if same-LLM skip |
| `multi_subagent_mode` | `false` by default; `true` only when the user explicitly requested multiple subagents |
| `findings` | Merged, deduplicated findings with `source` and optional `consensus` |
| `accepted` | Findings proven real by the main agent |
| `rejected` | Findings disproven, obsolete, duplicate, speculative, or out of scope |
| `fixed` | Accepted findings fixed in this round |
| `verification` | Tests, linters, builds, smoke checks, or manual evidence |

Stop early when a review round returns no actionable findings and verification passes. Stop after round 3 even if findings remain, and report unresolved items instead of starting round 4.

## Review Subagent Selection

### Subagent types (cost-effective)

| Scenario | Subagent | Constraints |
| --- | --- | --- |
| Cursor, default slot | `bugbot` | `readonly: true`; map Review Context Pack to `review-bugbot` prompt shape |
| Cursor, multi-subagent + security boundaries | `security-review` | `readonly: true`; map pack to `review-security` prompt shape |
| Non-Cursor or extra heterogeneous LLM | `generalPurpose` | `readonly: true`, explicit `model`, full Review Context Pack as `prompt` |
| **Forbidden for review** | `gpt-5.3-codex-high` and other implementation-grade models | Reserve for fixes after adjudication |

For `generalPurpose` review models, prefer fast/medium tiers from **different families** (e.g. `composer-2.5-fast`, `gpt-5.6-sol-medium`, `cursor-grok-4.5-high-fast`). In multi-subagent mode, never repeat the same `model` across slots.

### Subagent count

| Mode | Trigger | Subagents |
| --- | --- | --- |
| **Default** | User did not request multiple subagents | **1** (Cursor: `bugbot` if heterogeneous; else one `generalPurpose`) |
| **Multi-subagent** | User explicitly requested multiple reviewers | Up to **3**, each a different LLM from the main agent and from each other |

Multi-subagent slot fill (only after user opt-in):

1. Slot 1: `bugbot` if available and heterogeneous with main agent; else one `generalPurpose` with a different `model`.
2. Slot 2: `security-review` if changes touch auth, secrets, permissions, crypto, injection, external I/O, payments, or contracts—and the subagent LLM differs from the main agent.
3. Slot 3: Another `generalPurpose` with a different `model` family than main agent and existing slots.

Do **not** auto-fill to three subagents without user request.

### Same-LLM skip

Before dispatching any subagent:

1. Identify the main agent's current `model` or backend.
2. Identify the candidate subagent's `model` or backend (`bugbot` and `security-review` count as their platform-default review backends).
3. If they match, **skip that subagent**. Do not dispatch a redundant same-LLM reviewer.

If every candidate subagent would share the main agent's LLM, run **main-agent-only review** for that round. Record `subagents: []` and note same-LLM skip in the final report.

In multi-subagent mode, skip only the colliding slots; still dispatch remaining heterogeneous subagents.

### Main-agent parallel review

In the same turn as subagent dispatch, the main agent independently:

- Reviews using the packed scope, diff, and affected-path summary.
- Records findings in the standard format with `source: main-agent`.
- Stays read-only during this step—no code edits yet.
- Does **not** auto-accept its own findings; they enter merge and adjudication like any other source.

Dispatch subagent Task call(s) and main-agent read/trace tool calls in the **same response** so they run in parallel.

## Round Workflow

1. Snapshot and pack context.
   - Run the repo's normal status command, such as `git status --short --branch` when available.
   - Identify `ReviewScope`: unstaged changes, staged changes, branch changes, a PR diff, selected files, or all local changes.
   - Capture `git diff --stat` and the full diff, or a per-file change description when diff is unavailable.
   - If `affected-path-review` applies, add the affected behavior and path summary.
   - Add prior-round raw facts only: fixes made, tests run, rejected findings. Do not leak desired conclusions.
   - Fill one **Review Context Pack** (below) for subagent reuse.
   - Do not revert unrelated user changes.

2. Parallel review pass.
   - **Main agent:** Review the packed scope independently; record `main_agent_findings`.
   - **Subagent(s):** By default, dispatch one heterogeneous readonly subagent with the Review Context Pack. If the user requested multi-subagent mode, dispatch up to three, applying same-LLM skip per slot.
   - All subagents: `readonly: true`; do not edit, commit, or fix.
   - Complete main-agent review during subagent runtime, not after it returns.

3. Merge findings.
   - Combine `main_agent_findings` and all subagent findings.
   - Deduplicate by `file:line` and problem semantics.
   - Mark `consensus` when two or more sources flag the same issue. Consensus raises investigation priority only—it does not auto-accept.
   - On conflict, keep both rationales; the main agent verifies independently in the next step.

4. Adjudicate every finding locally.
   - Read the referenced code yourself—including findings you wrote as main agent.
   - Trace the relevant data flow, write path, error path, and tests.
   - Classify each finding as `accepted`, `rejected`, `already-fixed`, or `needs-user-decision`.
   - Reject speculative advice that lacks a concrete failing behavior, regression risk, or maintainability risk tied to the requested scope.

5. Fix accepted findings.
   - For behavior changes and bug fixes, write or update a failing regression test first, confirm it fails for the expected reason, then implement the smallest fix.
   - For high-stakes logic, verify units, permissions, precision, selectors, transactions, migration effects, and rollback paths from source-of-truth code or read-only probes where feasible.
   - For purely mechanical changes such as formatting, typo fixes, or dead comments, explain why no regression test applies and run the relevant formatter or static check.
   - Do not weaken tests to satisfy the implementation.

6. Verify before the next round.
   - Run focused tests for each fix.
   - Run the smallest useful broader suite, build, linter, or smoke command for the repo.
   - If verification fails, debug and fix before the next review round.

7. Decide whether to continue.
   - Continue to the next round only if code changed in the current round and fewer than three rounds have run.
   - Stop if no findings were accepted, no code changed, and verification passed.
   - Stop and ask the user if a finding requires product judgment, destructive action, secrets, credentials, paid services, or production writes.

## Review Context Pack

One pack per round, reused for every subagent. The main agent reviews against the same fields.

```text
Goal: Review round {N} local changes; return actionable findings only
Repo: <absolute repository path>
ReviewScope: <uncommitted changes | branch changes | file list>
Diff: <one of: branch changes, uncommitted changes, natural language>
BaseBranch: <only when Diff is branch changes and non-default base>
ChangeDescription: <required for natural language or when diff unavailable>
PriorRoundFacts: <fixes made, tests run, rejected findings — raw facts only>
AffectedBehavior: <optional; from affected-path-review>
Focus: bugs, regressions, missing tests, edge cases, security, data loss, performance, behavior mismatches
CustomInstructions: <optional user focus>
DoNot: edit files, commit, push, fix findings, inherit main-agent conclusions
Return: severity P0–P3, file:line/symbol, problem, why wrong, suggested verification; or explicit no-actionable-issues
```

**Mapping to subagent prompts:**

- `bugbot` / `security-review`: map to `Full Repository Path`, `Diff`, optional `Base Branch`, `Change Description`, `Custom Instructions` per those skills.
- `generalPurpose`: pass the full pack as `prompt`.

## Common Failure Modes

| Rationalization | Required behavior |
| --- | --- |
| "The reviewer said it, so I should fix it." | Verify independently before editing. |
| "Wait for the subagent before reading code." | Main agent and subagent(s) review in the same turn. |
| "I found it myself, so skip adjudication." | All findings, including `main-agent`, go through merge and adjudication. |
| "Dispatch a subagent even though it's the same LLM." | Same-LLM skip; main-agent-only review is valid. |
| "User didn't ask, but three reviewers is better." | Default to one subagent; multi-subagent requires explicit user request. |
| "Use Codex high for review quality." | Use bugbot/readonly reviewers; implementation models for fixes only. |
| "Let the subagent discover scope." | Pack Review Context Pack before dispatch. |
| "Consensus means auto-fix." | Consensus only raises priority; verify before accepting. |
| "One clean review is enough after several fixes." | Enough only if verification also passes. |
| "A third round found more issues, so continue." | Stop after round 3 and report remaining risks. |
| "This is small, tests can come after." | For behavior changes, create the failing test first. |
| "The subagent can fix it faster." | Subagents review only; the main agent owns fixes. |
| "The finding sounds plausible." | Plausible is `needs-investigation`, not `accepted`. |

## Final Report

Report:

- Review rounds run and why the loop stopped.
- Whether `multi_subagent_mode` was active.
- Subagents dispatched (type + model), or same-LLM skip with `subagents: []`.
- Main-agent finding count vs subagent finding count, and consensus count after merge.
- Findings accepted, rejected, already fixed, or requiring user decision.
- Files changed by the main agent.
- Verification commands and pass/fail results.
- Any unresolved risks after round 3.

Do not claim the code is clean unless the final review round has no actionable findings and verification passed in the current turn.
