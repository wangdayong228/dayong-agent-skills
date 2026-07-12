---
name: openapi-from-sources
description: Assembles OpenAPI 3.x from existing source materials (strict-api-extraction output, markdown, partial openapi.json). Runs strict readiness first; on NO-GO presents four numbered user options including example-fallback when official schema is incomplete. Do NOT fetch docs — use strict-api-extraction upstream. Do NOT codegen clients — use api-client-generator downstream.
---

# OpenAPI From Sources

## Core Rule

Assemble OpenAPI 3.x **only from evidenced source text** (Tier A/B). Never guess undocumented fields, types, enums, defaults, or status codes. Tier C reports (`docs/api-source-report.md`) guide discovery but are not evidence.

**Violating the letter of these rules is violating the spirit of these rules.**

## When to Use / NOT

**Use:** materials already collected; user asks to generate or reconstruct `openapi.yaml`; validating whether sources are ready for schema work.

**NOT:** need to crawl docs → `strict-api-extraction`; complete trusted spec already pinned → use as-is; client codegen → `api-client-generator`; JSON-RPC → out of scope for v1.

## Scope Boundary

Upstream `strict-api-extraction` Gate **GO** does **not** imply schema Gate **GO**. Extraction may mark items `missing_from_docs`; strict schema assembly treats those as blocking unless the user chooses an explicit follow-up option.

Deliver **readiness report** always. Deliver **`schema/openapi.yaml`** only on schema Gate **GO** or user-approved `example-fallback`.

## Input Profiles

**A — strict-api-extraction layout:**

```text
source/raw/           # Tier A
source/snapshots/     # Tier B
.firecrawl/           # Tier B auxiliary
docs/api-source-report.md   # Tier C index (not evidence)
```

**B — ad-hoc:** user-provided directory; inventory files and assign tier (machine-spec/json/yaml = A; captures = B).

Record in readiness report: profile, dialect (`OpenAPI 3.x`), scope (endpoints/operations), strictness (`strict` — default, or user-approved `example-fallback`).

If scope or material root is unclear, ask before preflight.

## Evidence & Conflicts

| Tier | Typical location | Conflict rank |
| --- | --- | --- |
| A | `source/raw/` | 1 |
| B | `source/snapshots/` | 2 |
| B | `.firecrawl/` | 3 |

Every schema element needs `x-source-evidence` with `path:line` (see `references/evidence-extensions.md`). Resolve conflicts by tier rank; record conflicts in readiness report.

## Readiness Checklist

Every in-scope item: `sourced`, `N/A`, `out_of_scope`, or `missing`.

| Element | Required for GO |
| --- | --- |
| Endpoint | path + HTTP method with Tier A/B evidence |
| Parameters | name, `in`, type, required/optional |
| Request body | content-type + schema; GET → `N/A` |
| Responses | each documented status: body schema or explicit no body |
| Response schemas | formal field types (not example-only) |
| Authentication | scheme + header/param name |
| Servers | `servers.url` |
| Errors | global or per-endpoint documented shapes |
| Cross-references | referenced enum/type pages present in materials |

**Schema Gate GO (strict):** every in-scope item is `sourced`, `N/A`, or user-approved `out_of_scope`. Any `missing` → **NO-GO** — write gap report with user options, then stop.

## NO-GO User Options

When strict mode is **NO-GO**, write `## User Decision Required` with exactly these options and ask the user to reply with a number:

1. **Re-fetch** — run `strict-api-extraction` for additional official pages.
2. **Example fallback** — generate schema from documented Tier A/B examples and mark inferred fields with `x-inferred-from: example`.
3. **Reduced scope** — exclude missing elements from the spec (`out_of_scope`) and generate only the sourced contract.
4. **Stop** — keep `docs/openapi-readiness-report.md` only; do not write `schema/openapi.yaml`.

Do not proceed with option 2 or 3 without explicit user approval.

## Workflow

1. **Intake** — material root, profile A/B, scope, strictness (`strict` unless user already selected `example-fallback`)
2. **Inventory** — list evidence files with tier, `source_url` if known, role
3. **Preflight** — run Readiness Checklist against Tier A/B only
4. **Gate** — **GO** or **NO-GO** (strict)
5. **If NO-GO** — write the four numbered user options and stop
6. **If user selects option 2** — re-run with `strictness: example-fallback`
7. **Assemble** (GO or example-fallback only) — merge in order: pinned complete openapi.json → embedded OpenAPI fragments in markdown → field-level extraction; enrich auth/errors from cross-ref pages
8. **Annotate** — add `x-source-evidence` on operations, parameters, schemas; add `x-inferred-from: example` on every example-derived schema element
9. **Validate** — valid OpenAPI 3.x; no element without evidence
10. **Deliver** — `docs/openapi-readiness-report.md`; `schema/openapi.yaml` only on GO or example-fallback

Load `references/readiness-report-template.md` before writing the report.

## Assembly Rules

- Start from the highest-tier complete fragment when present (e.g. embedded OpenAPI in endpoint markdown).
- Do not copy example JSON types into schema in `strict` mode.
- In `example-fallback`, infer only fields present in Tier A/B examples and add `x-inferred-from: example` plus `x-source-evidence`.
- Do not fill empty official schema objects from examples in strict mode.
- Pin `openapi` version field to `3.0.x` or `3.1.x` matching source; normalize to valid OpenAPI 3.x.
- Include only in-scope paths; document excluded paths as `out_of_scope` in report.

## No-Guess

Forbidden without Tier A/B text: infer types from examples; invent enums; assume required/optional; add status codes; use SDK or third-party specs; use training data.

| Excuse → Reality |
| --- |
| "Extraction report says GO" → extraction GO ≠ schema GO; re-run checklist on Tier A/B |
| "Example shows string" → examples ≠ schema in strict mode; ask before `example-fallback` |
| "Partial openapi has empty properties" → missing, not inferrable |

**STOP:** writing `schema/openapi.yaml` before schema Gate **GO**; citing report without `path:line`; silently filling missing schema properties.

## Deliverables

| Schema Gate | Files |
| --- | --- |
| **GO** | `schema/openapi.yaml`, `docs/openapi-readiness-report.md`, optional `schema/evidence-map.yaml` |
| **GO (example-fallback)** | `schema/openapi.yaml` with `x-inferred-from: example`, `docs/openapi-readiness-report.md` |
| **NO-GO** | `docs/openapi-readiness-report.md` only — gaps + the four numbered user options; do not delete an existing `schema/openapi.yaml` from a prior run |

After **GO**, suggest `api-client-generator` for client work.

## Verification

After a run, validate output:

```bash
./skills/dy-api-extraction/openapi-from-sources/scripts/validate-readiness-output.sh \
  /path/to/run-dir \
  skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/expected-readiness.yaml
```

Reference generator for fixture tests (strict mode):

```bash
./skills/dy-api-extraction/openapi-from-sources/scripts/generate-openapi-from-sources.sh \
  /path/to/material-root /path/to/output-dir
```

Example-fallback fixture mode:

```bash
./skills/dy-api-extraction/openapi-from-sources/scripts/generate-openapi-from-sources.sh \
  /path/to/material-root /path/to/output-dir --strictness example-fallback
```

Offline generation test from committed fixture:

```bash
./skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/verify.sh
```

## References

- Readiness report template: `references/readiness-report-template.md`
- Evidence extensions: `references/evidence-extensions.md`
