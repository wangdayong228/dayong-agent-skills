---
name: affected-path-review
description: >-
  Use when a Superpowers written Plan has completed every Task and a
  whole-branch/final code review is starting, or when the user explicitly
  asks to use affected-path-review. Do not use for per-task, task-reviewer,
  spec-compliance, plan/spec, or review-comment passes, iterative-code-review
  by default, or any other review unless the user explicitly opted in.
---

# Affected Path Review

## When to Use

Load only if one of these is true:

- Superpowers Plan has no remaining Tasks, and the next action is the
  whole-branch/final code review.
- The user explicitly asked to use affected-path-review in this invocation.

## When NOT to Use

Do not load for per-task reviews, plan/spec reviews, review comments,
verification, finishing, or iterative-code-review unless the user opted in.

## Core Rule

Review changed behavior, not just changed files.

Before reviewing findings or dispatching reviewers, identify the behavior affected by the change and inspect the code path that participates in that behavior. Do not restrict scope to the diff unless the user explicitly requests a diff-only review.

## Workflow

1. Name the affected behavior.
   - State the user-visible action, API behavior, background job, CLI command, data transformation, or side effect that can change.
   - If the changed lines are a helper, identify the callers and the behavior they support.

2. Trace source to sink.
   - Find where inputs originate.
   - Follow validation, normalization, defaults, fallbacks, transformations, serialization, estimation, execution, output, and error handling.
   - Include unchanged code on the path when it affects correctness.

3. Track transformed objects field by field.
   - For objects, payloads, transactions, requests, rows, files, messages, or command results, list the key fields.
   - Check whether any field is dropped, defaulted, renamed, reinterpreted, stale, partially validated, or represented differently across layers.

4. Review side-effect boundaries.
   - For writes, sends, deletes, migrations, payments, transactions, external API calls, notifications, generated files, or persisted state, inspect the final sink.
   - Confirm preview/dry-run/output semantics match what the sink will actually do.

5. Check tests against the affected path.
   - Verify tests cover the path from source to sink, not only the changed helper.
   - Report missing regression tests for any field, branch, default, fallback, or side-effect boundary that can affect behavior.

## Reviewer Prompt Add-On

When delegating a review, append this instruction:

```text
Do not restrict review to changed files. First identify the user-visible behavior or side-effect path affected by the change. Review all code that participates in that path, including unchanged callers, helpers, defaults, fallbacks, validation, serialization, estimation, execution, output, and tests. For every transformed object, trace key fields from source to sink and check whether any field is dropped, defaulted, renamed, reinterpreted, stale, or only partially validated.
```

## Findings Standard

Only report an affected-path finding when it has concrete evidence:

- the affected behavior or path
- the file and line or symbol
- the field, branch, fallback, side effect, or test gap involved
- why the current behavior is wrong or risky
- a focused verification command or regression test

Reject broad advice that cannot identify a behavior path, concrete risk, or testable failure mode.
