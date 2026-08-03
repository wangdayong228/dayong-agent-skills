# Evidence and Verification Rules

## Contents

- Evidence ranking
- Claim map
- Conflict handling
- Adaptive verification
- External and Git safety
- Completion standard

## Evidence Ranking

Rank current-behavior evidence:

```text
current executable code + passing tests
  > configuration, build scripts, and lock files
  > Active specifications
  > ordinary explanatory documentation
  > historical designs and plans
```

Code alone shows implementation; a passing behavior test raises confidence
that the behavior is intentional and current. Do not call a test "passing"
unless it was run successfully in this work.

## Claim Map

Maintain a transient map while writing:

```text
claim | source path and line or test | evidence tier | normative destination
```

Use it for exact routes, fields, defaults, limits, status codes, state
transitions, configuration precedence, process lifecycle, build constraints,
and platform support. Do not commit the map unless the user requests an audit
artifact.

## Conflict Handling

- Code and passing tests agree: document their behavior.
- Active spec disagrees: update the current doc to implementation evidence and
  report the difference.
- Code and tests disagree: do not guess. Block the affected claim, show both
  sources, and continue unrelated documentation.
- Ordinary docs disagree with stronger evidence: correct, move, or label them
  according to the approved file table.
- Only historical text supports a claim: describe it as history, not current
  behavior.

Never change business code under this skill. A behavior mismatch may justify a
separate code task, but not an unapproved implementation fix.

## Adaptive Verification

After the write gate is approved:

1. Run tests directly supporting normative claims.
2. Run the full local suite when repository size and duration are reasonable.
3. Validate changed Markdown links and image targets.
4. Parse exported SVG and confirm source/output pairs exist.
5. Check terminology, component names, paths, and interface direction.
6. Scan changed docs for unfinished markers, placeholders, empty headings,
   and unchecked implementation claims.
7. Inspect Git diff for duplication, unintended files, and whitespace errors.
8. Compare module links and normative destinations across the documentation.

Use repository-native commands. Do not install missing runners without
approval. If a runner is unavailable, report it as skipped and use only safe
existing alternatives; do not silently redefine the planned test.

## External and Git Safety

Default verification is local and deterministic. Network services, credentials,
paid APIs, production systems, package installation, and GUI application
launches require the applicable authorization.

Git delivery is selected in the approved proposal:

- `files only`: do not stage or commit;
- `commit`: stage only approved paths and commit after verification;
- `commit and push`: push only the verified commit to the named remote/branch.

An approval for one repository, branch, or earlier task does not authorize
another.

## Completion Standard

The final report separates:

- `passed`: exact command and observed result;
- `failed`: exact command, failure, and affected deliverable;
- `skipped`: reason and what remains unproved.

Do not say complete when a required engineering diagram cannot export, a
required link is broken, a normative claim is blocked, or an approved visual
is unresolved. A skipped optional infographic may coexist with complete prose
only when the user explicitly chose to skip it.
