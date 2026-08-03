# Visual Guidelines

## Contents

- Proposal scope
- Engineering diagrams
- Architecture infographics
- Qualifying orchestration model
- Missing capability branches
- Inspection and repair

## Proposal Scope

Recommend and approve each visual independently. Before generation, list its
reader, question answered, source evidence, output path, format, and whether it
is normative.

System visuals explain the whole request path and major boundaries. Module
visuals reduce scope to the selected module and its immediate consumers and
dependencies.

## Engineering Diagrams

- Editable source: `.drawio`.
- Embedded documentation output: `.svg`.
- Show precise components, interfaces, dependency direction, data flow, and
  selected code entry points.
- Prefer readable navigation over exhaustive nodes.
- Use consistent component names and colors across system/module diagrams.

Detect an available Draw.io export interface, not merely an application bundle
or executable path. Common candidates include `drawio`, `draw.io`, or on macOS
`/Applications/draw.io.app/Contents/MacOS/draw.io`. During the read-only audit,
run a non-mutating help/version probe when supported and distinguish:

- a verified CLI that accepts export arguments;
- a GUI-only application whose executable rejects CLI export arguments;
- an unknown interface that still requires a bounded export trial.

An installed application is not proof of CLI export capability. Use a verified
export interface rather than inventing a rendered SVG unrelated to the source.

After export, parse the SVG, inspect it visually, and check text, arrow
direction, clipping, contrast, and correspondence with the `.drawio` source.
If export capability is missing, report the engineering visual as blocked and
ask how to proceed. If export fails only after approved files are being
written, do not leave Markdown linked to a missing SVG. Keep or remove the
unexported `.drawio` source only through an approved operation-table update,
mark the engineering visual incomplete, and offer retry, explicit skip, or a
different authorized exporter.

## Architecture Infographics

- Output: PNG.
- Purpose: illustrated architecture information graphic with high-level
  component labels and principal flow.
- Status: non-normative; precise facts remain in prose, Specs, and engineering
  diagrams.
- Generate one initial option, not a gallery.
- Avoid dense fields, status codes, code paths, or tiny text.
- Keep labels short and inspect every rendered label for corruption.

Do not require a Draw.io source for the PNG.

## Qualifying Orchestration Model

The agent that owns repository evidence review, visual brief, prompt, render
call, inspection, and repair must be explicitly known to meet at least:

```text
model: gpt-5.6-sol
reasoning: high
```

`xhigh`, `max`, and `ultra` also qualify. A newer model qualifies only when
available metadata explicitly establishes it is at least equivalent; never
infer qualification from an unknown name.

If the main agent cannot prove qualification and model-selectable subagents
exist, spawn `gpt-5.6-sol` with `high` reasoning. The qualifying agent must load
the relevant code evidence and this visual brief. When available, use the
`imagegen` skill for the render call.

The platform image-generation renderer creates pixels. Do not call that
renderer GPT-5.6 unless the platform explicitly exposes that identifier.

## Missing Capability Branches

If no qualifying reasoning agent is available, ask the user to choose:

1. authorize a named available-model exception;
2. skip the infographic;
3. wait for a qualifying agent.

If no image-generation renderer is available, explain that changing the
reasoning model cannot render a PNG and ask the user to choose:

1. connect or enable an image generator;
2. skip the infographic;
3. wait for rendering capability.

Never silently downgrade either capability.

## Inspection and Repair

Inspect:

- component count, names, and relationships;
- primary flow direction;
- missing or invented components;
- corrupted labels;
- misleading security/trust implications;
- legibility at documentation size;
- consistency with the engineering diagram.

Generate at most two repair attempts after the initial image. Repair one
identified defect set at a time. If still unacceptable, stop and ask the user
whether to skip, accept with an explicit limitation, or revise the visual
brief.

An infographic failure does not invalidate verified prose or engineering
diagrams, but the final report must mark the approved PNG incomplete.
