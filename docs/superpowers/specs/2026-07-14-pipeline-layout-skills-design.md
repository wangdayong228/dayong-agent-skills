# Pipeline Layout for dy-api-extraction Skills

Date: 2026-07-14

## Context

`dy-api-extraction` contains three sequential skills that currently write stage outputs to the **target repository root**:

| Stage | Skill | Old default locations |
| --- | --- | --- |
| 1 | `strict-api-extraction` | `source/raw/`, `source/snapshots/`, `docs/api-source-report.md` |
| 2 | `openapi-from-sources` | `schema/openapi.yaml`, `docs/openapi-readiness-report.md` |
| 3 | `typed-sdk-from-openapi` | `generated/`, `pkg/client/`, `sdk/`, `scripts/`, plus a deliverable copy at `schema/openapi.yaml` |

When the target project is a publishable Go SDK, this mixes **pipeline/maintainer artifacts** with **consumer deliverables** at the same top level.

## Goal

Make stage 1–2 outputs land under `pipeline/` by default so a consumer-facing SDK repo keeps a clean top level. Stage 3 keeps delivering the Go module surface consumers import.

## Decisions Locked

| Decision | Choice |
| --- | --- |
| Layout style | Plan A: `pipeline/` holds stages 1–2 |
| Compatibility | **Breaking** — single new default; no `workspace-flat` / old-path dual mode |
| Orchestrator skill | **Not** added; only update the three existing skills |
| Scope of this work | **Skills only** (`dayong-agent-skills`); do **not** migrate `coinglass-sdk` in this change |
| Generated code location | `internal/generated/` (not root `generated/`) |
| SDK metadata dir rename | `sdk/` → `config/` |
| Regen / codegen config | `scripts/` → `tools/` |
| Spec copy in deliverable | **Remove** mandatory top-level `schema/openapi.yaml` copy; manifest points at input path (typically `pipeline/openapi/openapi.yaml`) + SHA256 |

## Non-Goals

- New `pipeline` / megaskill that merges stages 1–3 into one skill body
- Migrating existing consumer repos (e.g. `coinglass-sdk`) — follow-up
- Changing evidence tiers, schema gates, NO-GO user options, or retry-policy confirmation semantics
- Dual-layout profile or path aliases for old paths

## Target Project Layout (after skills run)

```text
<project>/
├── pkg/client/                         # stage 3 deliverable
├── internal/
│   ├── transport/                      # stage 3 deliverable
│   └── generated/                      # stage 3 generated client
├── config/
│   ├── retry-policy.yaml
│   └── spec-manifest.yaml
├── tools/
│   ├── regen.sh
│   └── oapi-codegen.yaml
├── go.mod
├── go.sum
└── pipeline/
    ├── extract/
    │   ├── raw/                        # Tier A (gitignore)
    │   ├── snapshots/                  # Tier B
    │   └── report.md                   # Tier C
    └── openapi/
        ├── openapi.yaml                # canonical OpenAPI contract
        ├── evidence-map.yaml           # optional
        └── readiness-report.md

.firecrawl/                             # Tier B auxiliary (gitignore)
.sdkgen/                                # stage 3 intermediates (gitignore)
.local/                                 # gitignore
```

## Path Migration Map

| Old path | New path | Owner skill |
| --- | --- | --- |
| `source/raw/` | `pipeline/extract/raw/` | strict-api-extraction |
| `source/snapshots/` | `pipeline/extract/snapshots/` | strict-api-extraction |
| `docs/api-source-report.md` | `pipeline/extract/report.md` | strict-api-extraction |
| `schema/openapi.yaml` | `pipeline/openapi/openapi.yaml` | openapi-from-sources |
| `schema/evidence-map.yaml` | `pipeline/openapi/evidence-map.yaml` | openapi-from-sources |
| `docs/openapi-readiness-report.md` | `pipeline/openapi/readiness-report.md` | openapi-from-sources |
| `generated/` | `internal/generated/` | typed-sdk-from-openapi |
| `sdk/` | `config/` | typed-sdk-from-openapi |
| `scripts/regen.sh` | `tools/regen.sh` | typed-sdk-from-openapi |
| Deliverable `schema/openapi.yaml` | removed; use pipeline (or pinned input) + manifest | typed-sdk-from-openapi |

`.firecrawl/` and `.sdkgen/` stay at project root (gitignored).

## Per-Skill Changes

### strict-api-extraction

- Update Tiers/Storage table, Capture table, Workflow, Deliverable, STOP, and evidence citation text to new extract paths.
- Target `.gitignore` guidance: `.local/`, `.firecrawl/`, `pipeline/extract/raw/` (stop recommending `source/raw` / `source/snapshots` as the primary raw store; snapshots may still be committed when short).
- Update `references/report-template.md` examples and downstream pointer to `pipeline/openapi/openapi.yaml`.
- Update `agents/openai.yaml` prompts/descriptions.

### openapi-from-sources

- Profile A input layout becomes `pipeline/extract/{raw,snapshots,report.md}` + `.firecrawl/`.
- Profile B (ad-hoc user directory) remains; only the official layout defaults change.
- Deliverables: `pipeline/openapi/openapi.yaml`, `pipeline/openapi/readiness-report.md`, optional `evidence-map.yaml`.
- Update Workflow, NO-GO options, STOP, Runtime Validation, and all references (`readiness-report-template.md`, `evidence-extensions.md`, `fixture-tests.md`, `agents/openai.yaml`).
- Evidence path examples use `pipeline/extract/...`.
- Downstream hint points `typed-sdk-from-openapi` at `pipeline/openapi/openapi.yaml`.

### typed-sdk-from-openapi

- Preferred input: `pipeline/openapi/openapi.yaml` (still accept an explicit user-pinned path to any OpenAPI 3.x file).
- Final deliverable module:

```text
<output>/
  internal/generated/client.gen.go
  internal/transport/{transport.go,errors.go,operation.go,retry.go}
  pkg/client/...
  config/spec-manifest.yaml
  config/retry-policy.yaml
  tools/regen.sh
  tools/oapi-codegen.yaml
  go.mod
  go.sum (optional)
```

- Drop workflow step that copies/normalizes the input into a top-level deliverable `schema/openapi.yaml`.
- Manifest records input spec path + SHA256 + generation timestamp.
- Regen emits into `internal/generated/`.
- Update Core Rule, Input Requirements, Output Model, SDK Gate, Workflow, Runtime Validation, and references (`refined-client-patterns.md`, `transport-patterns.md`, `fixture-tests.md`, `sdk-readiness-report-template.md`).
- Retry policy finalized path: `config/retry-policy.yaml`.

## Cross-Skill Contract

```text
strict-api-extraction
  → pipeline/extract/*

openapi-from-sources
  ← pipeline/extract/*
  → pipeline/openapi/openapi.yaml (+ readiness report)

typed-sdk-from-openapi
  ← pipeline/openapi/openapi.yaml (or explicit pin)
  → pkg/ + internal/ + config/ + tools/
```

Stage semantics (GO/NO-GO, evidence rules, retry confirmation) are unchanged; only file locations change.

## Repository Documentation

Update `dayong-agent-skills/README.md` skill descriptions that still cite old paths (`source/raw`, `schema/openapi.yaml`, root `generated/`). Add a short **BREAKING CHANGE** note for this layout switch.

## Success Criteria

1. Under `skills/dy-api-extraction/`, no skill doc treats the old root paths as default outputs.
2. Stage 1 → 2 → 3 path references are consistent.
3. Gates, NO-GO options, tiers, retry confirmation, and RoundTripper rules are unchanged in meaning.
4. Gitignore guidance lists `pipeline/extract/raw/`, `.firecrawl/`, `.local/`, `.sdkgen/`.
5. README documents the breaking layout change.

## Follow-up (out of scope)

Migrate consumer repos such as `coinglass-sdk` to the new layout and re-point regen/manifest paths. Until then, running the updated skills against an old-layout repo will intentionally mismatch.
