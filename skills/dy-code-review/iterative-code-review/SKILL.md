---
name: iterative-code-review
description: Use when the user asks Codex to have a subagent, reviewer agent, or AI reviewer inspect local code changes and then have the main agent evaluate and fix issues until the code is clean.
---

# Iterative Code Review

## Overview

Run a bounded review loop: a subagent reviews the current code, the main agent adjudicates each finding, fixes only verified issues, then repeats until there are no actionable findings or three review rounds have completed.

The main agent remains accountable. Subagent feedback is evidence to evaluate, not instructions to obey.

## Required Sub-Skills

Before editing code, load the environment's relevant skills by capability:

- Subagent or multi-agent capability for the review pass.
- External-review evaluation capability before accepting or rejecting findings.
- Debugging/root-cause capability for bugs or surprising behavior.
- Test-first capability before behavior changes.
- High-stakes implementation/testing capability for money, security, permissions, data loss, contracts, transactions, migrations, or irreversible actions.
- Verification and consistency capability before claiming completion.

If the request is about GitHub PR comments or review threads, use `pr-comment-review` first, then use this skill only for the local subagent review loop.

## Loop Contract

Run at most three rounds. Track this state explicitly:

| Field | Meaning |
| --- | --- |
| `round` | 1, 2, or 3 |
| `review_scope` | Files, diff, PR, or command output reviewed |
| `findings` | Subagent findings with file, line, severity, and rationale |
| `accepted` | Findings proven real by the main agent |
| `rejected` | Findings disproven, obsolete, duplicate, speculative, or out of scope |
| `fixed` | Accepted findings fixed in this round |
| `verification` | Tests, linters, builds, smoke checks, or manual evidence |

Stop early when a review round returns no actionable findings and verification passes. Stop after round 3 even if findings remain, and report unresolved items instead of starting round 4.

## Round Workflow

1. Snapshot the workspace.
   - Run the repo's normal status command, such as `git status --short --branch` when available.
   - Identify the exact scope to review: unstaged changes, staged changes, a PR diff, selected files, or all local changes.
   - Do not revert unrelated user changes.

2. Dispatch one subagent review.
   - Ask for a code-review stance: bugs, regressions, missing tests, edge cases, security, performance risks, and behavior mismatches.
   - Require concrete evidence for every finding: file path, line or symbol, impact, why current behavior is wrong, and suggested verification.
   - Tell the subagent not to edit files.
   - Provide previous round context only as raw facts: fixes made, tests run, and findings already rejected. Do not leak desired conclusions.

3. Adjudicate every finding locally.
   - Read the referenced code yourself.
   - Trace the relevant data flow, write path, error path, and tests.
   - Classify each finding as `accepted`, `rejected`, `already-fixed`, or `needs-user-decision`.
   - Reject speculative advice that lacks a concrete failing behavior, regression risk, or maintainability risk tied to the requested scope.

4. Fix accepted findings.
   - For behavior changes and bug fixes, write or update a failing regression test first, confirm it fails for the expected reason, then implement the smallest fix.
   - For high-stakes logic, verify units, permissions, precision, selectors, transactions, migration effects, and rollback paths from source-of-truth code or read-only probes where feasible.
   - For purely mechanical changes such as formatting, typo fixes, or dead comments, explain why no regression test applies and run the relevant formatter or static check.
   - Do not weaken tests to satisfy the implementation.

5. Verify before the next round.
   - Run focused tests for each fix.
   - Run the smallest useful broader suite, build, linter, or smoke command for the repo.
   - If verification fails, debug and fix before dispatching the next review round.

6. Decide whether to continue.
   - Continue to the next round only if code changed in the current round and fewer than three rounds have run.
   - Stop if no findings were accepted, no code changed, and verification passed.
   - Stop and ask the user if a finding requires product judgment, destructive action, secrets, credentials, paid services, or production writes.

## Subagent Prompt Template

```text
Review the current local code changes as a code reviewer. Do not edit files.

Scope:
- [describe files/diff/PR/commands]

Focus on bugs, regressions, missing tests, edge cases, security, data loss,
performance risks, and behavior mismatches. Ignore style-only preferences unless
they hide a real correctness or maintainability problem.

For each finding, return:
- severity: P0/P1/P2/P3
- file and line/symbol
- concrete problem
- why current behavior is wrong
- suggested verification or regression test

If there are no actionable issues, say that clearly.
```

## Common Failure Modes

| Rationalization | Required behavior |
| --- | --- |
| "The reviewer said it, so I should fix it." | Verify independently before editing. |
| "One clean review is enough after several fixes." | It is enough only if verification also passes. |
| "A third round found more issues, so continue." | Stop after round 3 and report remaining risks. |
| "This is small, tests can come after." | For behavior changes, create the failing test first. |
| "The subagent can fix it faster." | This skill uses subagents for review only; the main agent owns fixes. |
| "The finding sounds plausible." | Plausible is `needs-investigation`, not `accepted`. |

## Final Report

Report:

- Review rounds run and why the loop stopped.
- Findings accepted, rejected, already fixed, or requiring user decision.
- Files changed by the main agent.
- Verification commands and pass/fail results.
- Any unresolved risks after round 3.

Do not claim the code is clean unless the final review round has no actionable findings and verification passed in the current turn.
