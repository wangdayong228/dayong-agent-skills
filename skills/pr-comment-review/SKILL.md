---
name: pr-comment-review
description: Use when asked to fetch, inspect, evaluate, address, or summarize the latest GitHub PR comments, review comments, Codex review feedback, or actionable PR review threads for the current branch or a specified PR.
---

# PR Comment Review

## Overview

Use this as the single workflow for PR review feedback: fetch the latest PR comments, decide what is still actionable, verify against the current code, then fix only confirmed issues with tests.

## Skill Handling

Use this skill as the entry point. Before fetching comments or changing code, enter the environment's normal skill-selection workflow and load the minimal relevant skills available in the current session.

Select by capability, not by a hard-coded skill list:

- PR/GitHub capability for PR discovery, comment retrieval, and review threads.
- External-review evaluation capability before accepting or rejecting feedback.
- Debugging/root-cause capability for bugs, reverts, failed transactions, or unexpected behavior.
- Test-first capability before code changes.
- High-stakes implementation/testing capability for money, DeFi, gas, contract selectors, contracts, permissions, security, or irreversible effects.
- Verification and consistency capability before claiming completion.
- Commit capability only when the user asks to commit.

If no matching skill exists for a needed capability, state that gap and continue with the equivalent workflow manually.

## Workflow

1. Resolve the PR.
   - If the user gives a PR URL/number, use it.
   - Otherwise inspect the current branch with `git status --short --branch`, `git remote -v`, and `gh pr view --json number,title,url,headRefName,baseRefName,updatedAt`.
   - If `gh pr view` cannot find it, search with `gh pr list --head <branch> --state all --json number,title,url,updatedAt`.

2. Fetch comments and review threads.
   - Prefer the GitHub connector when available, especially `_fetch_pr_comments` and `_list_pull_request_review_threads`.
   - Use `gh pr view <number> --json comments,reviews,reviewDecision,latestReviews` when connector data is unavailable or incomplete.
   - Sort by creation/update time and identify comments newer than the last handled commit or obviously still unresolved.

3. Classify each comment.
   - `already-fixed`: current code or later commits address it.
   - `actionable`: the comment describes a real bug, revert risk, wrong behavior, missing guard, missing test, or transaction/gas/security issue.
   - `needs-investigation`: plausible but not proven; gather evidence before editing.
   - `not-actionable`: obsolete, duplicate, incorrect, or outside scope.

4. Verify before accepting feedback.
   - Read the referenced file and line.
   - Trace the relevant data flow and write path.
   - For blockchain/financial logic, verify units, selectors, balances, oracle values, factors, and write effects from source code or read-only chain probes.
   - If feedback mentions a transaction selector, overload, revert, gas loss, or contract behavior, independently confirm with ABI/function selectors or read-only RPC evidence when feasible.

5. Fix actionable issues with regression coverage.
   - Write a failing test first for the behavior in the comment.
   - Confirm the test fails for the expected reason.
   - Make the smallest scoped code change.
   - Run the relevant test suite and any useful smoke command.
   - Do not weaken tests to match the current implementation.

6. Report clearly.
   - List latest comments inspected.
   - State which are already fixed, fixed now, still open, or rejected with reason.
   - Include verification commands and pass/fail results.
   - If code changed, mention files touched and whether the work is committed.

## Guardrails

- Do not treat external review feedback as automatically correct.
- Do not edit code before verifying the claim and creating a failing regression test for real bugs.
- Do not rely only on comment text for high-stakes logic; check source of truth.
- Do not claim "fixed" until tests and smoke checks have run in the current turn.
- Prefer false negatives over unsafe previews, writes, migrations, deletes, or transactions.

## Quick Commands

```bash
git status --short --branch
git remote -v
gh pr view --json number,title,url,comments,reviews,reviewDecision
gh pr list --head "$(git branch --show-current)" --state all --json number,title,url,updatedAt
```

Use `gh` with explicit `--repo owner/name` when the PR belongs to a fork or upstream repository.
