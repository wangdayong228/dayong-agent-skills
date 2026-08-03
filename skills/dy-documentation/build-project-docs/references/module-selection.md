# Module Selection

## Contents

- Conceptual module test
- Independent recommendations
- Verdicts
- Bulk approval table
- Default output
- Module overview contract

## Conceptual Module Test

A candidate deserves separate treatment when several of these are true:

- it has a stable, singular responsibility;
- consumers use a defined interface, protocol, or data model;
- it owns a meaningful lifecycle, state machine, data flow, or concurrency
  boundary;
- it can be tested, deployed, replaced, or evolved independently;
- multiple other components depend on it;
- its security, failure, cancellation, or operational behavior needs focused
  explanation;
- the system overview cannot explain it clearly in one or two paragraphs;
- enough stable evidence exists to avoid a thin page.

Source directories and packages are inventory evidence, not automatic modules.
Group small adapters, configuration loaders, and glue into their parent when
they lack an independent reader or maintenance boundary.

## Independent Recommendations

Score these separately:

### Module Document

Recommend when focused prose improves understanding or safe modification.

### Engineering Diagram

Recommend when components, dependencies, state, concurrency, or request flow
are materially clearer visually. Output is Draw.io source plus SVG.

### Architecture Infographic

Recommend when a high-level illustrated mental model helps readers. Do not
recommend merely because a module document exists.

## Verdicts

Use one:

- `generate independently`;
- `merge into parent`;
- `do not generate`.

Every verdict includes evidence, reader value, expected output count, and
maintenance cost. Do not use a numeric score without explaining the decision.

## Bulk Approval Table

After foundation review, present:

```text
candidate | boundary/evidence | document verdict | engineering diagram verdict | infographic verdict | files | maintenance cost
```

Recommend a set, but let the user add, remove, or combine candidates. One
approval covers the selected module batch only when the same message also
contains the complete per-file operation table:

```text
source/current path | action | destination/final path | content source | final responsibility
```

List every module page and approved visual plus every global/module navigation
edit. The recommendation table or a file count alone is not write
authorization. Internally process one module at a time and perform a final
cross-module consistency pass.

## Default Output

For an independently approved module:

```text
docs/architecture/modules/<module>/
├── overview.md
└── diagrams/
    ├── architecture.drawio
    ├── architecture.svg
    └── infographic.png
```

Generate only the approved visual subset. On the first module, create a module
navigation page only when it adds real navigation value; do not create an
empty index in advance.

## Module Overview Contract

Select only evidenced, useful sections:

- purpose and boundary;
- primary code entry points;
- public interfaces and dependencies;
- internal components;
- data flow and lifecycle;
- state, concurrency, cancellation, and error propagation;
- security and runtime constraints;
- how to build, test, and safely modify the module;
- links to system Architecture and normative Specs.

Exact protocol fields, defaults, limits, and errors remain in the relevant
Spec. The module overview links to them instead of duplicating them.

After the batch, update approved global/module navigation and verify interface
direction, terminology, and links across modules. Do not rewrite unrelated
foundation prose.
