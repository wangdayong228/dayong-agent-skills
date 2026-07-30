---
name: build-project-docs
description: Use when a repository needs a complete project documentation system, a mechanism-heavy README needs restructuring, current code must be documented across usage, architecture, spec, or development views, or system and module architecture docs and visuals need to be created or synchronized.
---

# Build Project Docs

## Core Principle

Ground current facts in executable code and passing tests. Before changing any
project file, obtain approval for both the information architecture and an
exact file-operation table.

An urgent request, a request to "just do it", or an instruction to commit does
not bypass this gate. Audit first, propose, obtain approval, then execute.

## Select the Mode

| Observable request | Mode | Result |
|---|---|---|
| Complete, restructure, or synchronize project docs | `full` | Foundation first; modules after foundation review |
| Explicitly says only plan/discuss or no file changes | `plan-only` | Read-only options and operation plan; stop |
| Names one existing module to document | `module-increment` | Target module plus necessary dependencies only |

Explicit skill invocation selects this workflow, not permission to skip its
approval gate.

## Load References

Read every selected reference completely before acting:

- Proposal or foundation work: `references/information-architecture.md`
- Factual writing or verification: `references/evidence-rules.md`
- Module assessment or generation: `references/module-selection.md`
- Any visual proposal or generation: `references/visual-guidelines.md`

References are one level deep. Do not partially preview a selected reference.

## Workflow

### 1. Audit Read-Only

Inspect repository entry points, processes, languages, build/test tools,
modules, APIs, protocols, configuration, tests, docs, diagrams, history, Git
status, and project instructions.

Do not create, edit, move, delete, stage, commit, push, install dependencies,
or run commands that write caches/artifacts during this phase.

### 2. Present 2–4 Tailored Options

Use the proposal contract from `information-architecture.md`. Options must be
derived from this repository, not generic labels. Include a five-category
README/Usage/Architecture/Spec/Development option, but do not force five
separate files when a merged option better fits.

Let the user choose one option, combine options, or revise them.

### 3. Present the Final Operation Table

Before writes, show the final tree and every affected path:

```text
source/current path | action | destination/final path | content source | final responsibility
```

For `move`, name both the current source and exact destination. For `merge` or
`delete`, name the destination for every retained fact. For `create`, use `—`
as the source and the new path as the destination. Also ask the user to select
one Git delivery mode:

- files only;
- files and commit;
- files, commit, and push.

Wait for explicit approval. If the user already supplied a complete structure,
restate the resolved tree and operation table and request one confirmation.

In `plan-only`, the selected option may be resolved into a hypothetical final
tree and exact operation table, but do not ask for a Git mode or execution
approval. Label it read-only and stop after presenting it.

### 4. Deliver the Foundation

Apply only approved operations. The foundation is complete for the selected
scheme:

- current README/navigation responsibility;
- approved Usage, Architecture, Spec, and Development responsibilities,
  whether separate or merged;
- approved system Draw.io source plus exported SVG;
- approved non-normative PNG architecture infographic.

Run adaptive verification, report evidence and skipped checks honestly, then
pause for foundation review.

In `plan-only`, stop before this step. Do not write a design artifact unless
the user separately requests one.

### 5. Assess Modules

After foundation review, use `module-selection.md`. Recommend module document,
engineering diagram, and infographic independently. Include reasons, output
count, and maintenance cost. In the same approval message, include an exact
module operation table using the Step 3 schema for every proposed module file
and every global or module navigation edit.

The user confirms the module verdicts and complete module operation table once.
The recommendation table alone is never write authorization. Internally
generate and verify one module at a time; deliver the approved module batch
once, without per-module interruptions.

In `module-increment`, perform this assessment for the named module and its
necessary dependencies, present the exact operation table and Git delivery
mode, then update only approved navigation links after confirmation.

### 6. Verify and Deliver

Use `evidence-rules.md`. Validate changed documentation links with:

```bash
python3 <skill-dir>/scripts/check_relative_links.py --root <repo-root> [changed-doc-path ...]
```

Execute only the selected Git mode. Push requires explicit approval even when
commit was approved.

## Required Proposal Contract

Every option contains, in this order:

1. name and one-sentence fit;
2. exactly one exhaustive numbered manifest of all in-scope documentation
   deliverables after execution: README/current docs, retained documentation
   history, and every `generate` visual. Exclude code, tests, and configuration
   used only as evidence. Prose-only manifests that omit generated visuals are
   forbidden. The last ordinal is the documentation-deliverable count, and an
   optional tree may visualize the same paths;
3. audiences and document responsibilities;
4. migration/retention/deletion summary;
5. the exact system-visual table below; module visual scope is stated
   separately;
6. estimated maintenance cost;
7. main trade-off and recommendation.

The final approved proposal additionally contains the exact operation table
and Git delivery mode.

Use this table in every option:

```text
visual | verdict | exact candidate output path(s) | created if approved? | reason
engineering diagram | generate/skip/blocked | .drawio and .svg paths | yes/no | ...
infographic | generate/skip/blocked | .png path | yes/no | ...
```

`skip` still names the paths that would be used, marks `created if approved?`
as `no`, and explains why no files will be created. Skipped candidate paths do
not appear in the final-file manifest and do not count toward its last ordinal.
`blocked` follows the same manifest/count rule and forbids partial creation,
including a source-only `.drawio`, until the blocker is resolved and the
proposal/table is refreshed as `generate` or `skip`. Do not replace candidate
paths with “none” or omit the row.

## External-System Boundary

Default to local, deterministic evidence. Before network access, credential
use, paid APIs, production access, or dependency installation, state the
purpose, command/tool, credential scope, and cost/risk, then obtain explicit
authorization.

Existing credentials or an urgent deadline are not authorization.

## Final Report Contract

Report:

1. created, updated, moved, merged, deleted, and retained files;
2. primary documentation and visual entry points;
3. verification commands grouped as passed, failed, and skipped;
4. implementation/documentation differences found and how they were handled;
5. unresolved blockers or risks;
6. Git commit and push status.

## Rationalizations to Reject

| Rationalization | Required response |
|---|---|
| "There is no time to ask" | Approval is part of correct documentation work; stop before writes. |
| "The Active spec is authoritative" | Current code plus passing tests outrank a stale spec; report the conflict. |
| "Every directory deserves a module page" | Directories are evidence, not module boundaries; apply the value rubric. |
| "A cheaper image model is fine" | Only the user can authorize an explicit model exception. |
| "A temporary install is harmless" | Installation is an external mutation and needs approval. |

## Red Flags

Stop and return to the appropriate gate if any occurs:

- project-file mutation before architecture and operation-table approval;
- commit or push inferred from urgency or earlier unrelated authorization;
- current behavior copied from history without code/test evidence;
- one module document created per source directory without assessment;
- image orchestration silently downgraded;
- skipped tests described as passing;
- user changes overwritten or deleted outside the approved table.
