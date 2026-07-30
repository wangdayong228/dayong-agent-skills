# Information Architecture

## Contents

- Read-only inventory
- Language choice
- Candidate options
- Five responsibility boundaries
- Current facts and history
- Proposal contract
- File-operation contract

## Read-Only Inventory

Inspect before proposing:

- root instructions and README;
- executable entry points and long-running processes;
- languages, frameworks, package/module/workspace manifests;
- build, test, lint, release, deployment, and configuration files;
- public APIs, protocols, schemas, persistence, and trust boundaries;
- unit, integration, end-to-end, and opt-in live tests;
- current docs, diagrams, ADR/RFC/spec/plan history;
- Git status, ignored paths, and existing user modifications.

Infer conceptual boundaries from responsibilities, dependencies, interfaces,
runtime flow, and tests together. A directory name alone is not architecture.

## Language Choice

Use the repository's dominant documentation language. If current docs have no
clear dominant language, ask before proposing final filenames. Do not create
bilingual duplicates by default. Preserve code identifiers, commands, protocol
fields, and product names verbatim.

## Candidate Options

Offer 2–4 options that fit the audited repository. Draw from these patterns,
but replace generic names with concrete trees and counts.

### Adaptive Minimal

Use for small projects. Merge responsibilities into fewer complete files.
Never omit an important responsibility merely to reduce file count.

### Five-Category Standard

Use README plus Usage, Architecture, Spec, and Development. Start each category
with one file; split only at a stable maintenance boundary.

### Extended

Add only evidenced needs such as Operations, Security, Troubleshooting,
Tutorials, ADR, or component-specific references. Explain why each extra
category cannot fit an existing responsibility.

### Conservative Restructure

Keep established paths where possible. Repair navigation, authority labels,
content boundaries, and missing facts. Move/merge/delete only when the benefit
outweighs link churn and migration cost.

## Five Responsibility Boundaries

| Responsibility | Answers | Owns | Does not own |
|---|---|---|---|
| README | What is this and where do I go? | value, scope, shortest path, global navigation | full manual or exact contract |
| Usage | How do I perform a user task? | prerequisites, setup, procedures, actionable failures | repeated exact limits/defaults |
| Architecture | What is composed how, and why? | boundaries, dependencies, flows, lifecycle, rationale, trust | exact fields/status codes |
| Spec | What behavior is currently guaranteed? | routes, fields, defaults, limits, states, errors, protocols | historical proposals |
| Development | How do I understand, build, test, and change it? | repository map, local workflow, test layers | end-user procedures |

When a minimal scheme merges files, keep these responsibilities distinct
inside the merged file. Exact facts retain one normative destination.

## Current Facts and History

Current docs are updated in place and normally undated. Historical decisions
may live in Superpowers specs/plans, ADRs, RFCs, proposals, or another existing
system. Preserve the repository's convention; do not create
`docs/superpowers/` merely because this skill knows that name.

History explains why. It never overrides current implementation evidence.
Label non-normative planning/manual material when readers could mistake it for
an active contract.

## Proposal Contract

For every candidate, provide:

```text
Option name — repository-specific fit
Numbered exhaustive final-file manifest (last ordinal = final file count)
Optional tree showing the same paths
Audience/responsibility map
Migration, retention, and deletion summary
System visual table:
  visual | verdict | exact candidate output path(s) | created if approved? | reason
Module visual scope
Maintenance cost: low/medium/high with reason
Main trade-off
Recommendation
```

Each option has exactly one numbered documentation-deliverable manifest. It
contains every in-scope artifact after executing that option: README/current
docs, retained documentation history, and every visual whose verdict is
`generate`. Code, tests, schemas, and configuration used only as evidence are
not deliverables and must not appear. Do not show a separate prose-only
manifest that omits generated visuals. The last ordinal is the deliverable
count. When a tree is shown, it contains the identical paths.

The two system visual rows are always present, even when their verdict is
`skip` or `blocked`. Every row names the exact candidate path that would be
used. For `skip`, mark `created if approved?` as `no`, state that no file will
be created, and exclude those candidate paths from the final-file manifest and
count. `blocked` uses the same `created = no` and exclusion rules: do not create
even a partial artifact until the user resolves the blocker and the proposal
and operation table are refreshed. Never write “no output path.”

The user may select, combine, or revise options. Resolve the selection into one
tree before presenting file operations.

## File-Operation Contract

Use:

```text
source/current path | action | destination/final path | content source | final responsibility
```

Allowed actions are `create`, `update`, `move`, `merge`, `delete`, and `keep`.
List every affected existing document, including historical/manual materials.

- `create`: source is `—`; destination is the exact new path.
- `update` or `keep`: source and destination are the same exact path.
- `move`: source and destination are both mandatory and different.
- `merge` or `delete`: identify the destination of every retained fact; use
  `—` only when the approved decision discards all content.

Do not create empty directories, placeholder pages, README files that only
repeat a directory name, or files too thin to maintain independently.

Existing uncommitted changes belong to the user. If an approved operation
overlaps them and cannot be applied safely, stop and request direction.
