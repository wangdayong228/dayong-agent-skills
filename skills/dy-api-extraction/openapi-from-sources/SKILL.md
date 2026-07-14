---
name: openapi-from-sources
description: Assembles OpenAPI 3.x from existing source materials (strict-api-extraction output, markdown, partial openapi.json). Runs strict readiness first; on NO-GO presents four numbered user options including example-fallback when official schema is incomplete. Do NOT fetch docs — use strict-api-extraction upstream. Do NOT codegen clients — use api-client-generator or typed-sdk-from-openapi (Go) downstream.
---

# OpenAPI From Sources

## Core Rule

Assemble OpenAPI 3.x **only from evidenced source text** (Tier A/B). Never guess undocumented fields, types, enums, defaults, or status codes. Tier C reports (`pipeline/extract/report.md`) guide discovery but are not evidence.

**Violating the letter of these rules is violating the spirit of these rules.**

## When to Use / NOT

**Use:** materials already collected; user asks to generate or reconstruct `openapi.yaml`; validating whether sources are ready for schema work.

**NOT:** need to crawl docs → `strict-api-extraction`; complete trusted spec already pinned → use as-is; client codegen → `api-client-generator` or `typed-sdk-from-openapi` (Go); JSON-RPC → out of scope for v1.

## Scope Boundary

Upstream `strict-api-extraction` Gate **GO** does **not** imply schema Gate **GO**. Extraction may mark items `missing_from_docs`; strict schema assembly treats those as blocking unless the user chooses an explicit follow-up option.

Deliver **readiness report** always. Deliver **`pipeline/openapi/openapi.yaml`** only on schema Gate **GO**, **GO (example-fallback)**, or **GO (reduced-scope)**.

## Input Profiles

**A — strict-api-extraction layout:**

```text
pipeline/extract/raw/           # Tier A
pipeline/extract/snapshots/     # Tier B
.firecrawl/           # Tier B auxiliary
pipeline/extract/report.md   # Tier C index (not evidence)
```

**B — ad-hoc:** user-provided directory; inventory files and assign tier (machine-spec/json/yaml = A; captures = B).

Record in readiness report: profile, dialect (`OpenAPI 3.x`), scope (endpoints/operations), strictness (`strict` — default; `example-fallback` after user option 2).

If scope or material root is unclear, ask before preflight.

## Evidence & Conflicts

| Tier | Typical location | Conflict rank |
| --- | --- | --- |
| A | `pipeline/extract/raw/` | 1 |
| B | `pipeline/extract/snapshots/` | 2 |
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
| Response schemas | **strict:** formal field types (not example-only). **example-fallback:** formal types where present; otherwise Tier A/B example inference with `x-inferred-from: example` |
| Authentication | scheme + header/param name |
| Servers | `servers.url` |
| Errors | global or per-endpoint documented shapes |
| Cross-references | referenced enum/type pages present in materials |

**Schema Gate GO (strict):** every in-scope item is `sourced`, `N/A`, or user-approved `out_of_scope`. Any `missing` → **NO-GO** — write gap report with user options, then stop.

**Schema Gate GO (example-fallback):** run only after user selects option 2. Every in-scope item is `sourced`, `N/A`, `out_of_scope`, or `inferred-from-example`. Empty official response schemas may be filled only from Tier A/B examples; every inferred field needs `x-inferred-from: example` and `x-source-evidence`. Any remaining `missing` → **NO-GO**.

**Schema Gate GO (reduced-scope):** run only after user selects option 3. User-approved blocking gaps are marked `out_of_scope` in the checklist and excluded from `pipeline/openapi/openapi.yaml`. Every **remaining** in-scope item is `sourced` or `N/A`. Any `missing` among remaining scope → **NO-GO**.

## NO-GO User Options

When strict mode is **NO-GO**, write `## User Decision Required` with exactly these options and ask the user to reply with a number:

1. **Re-fetch** — run `strict-api-extraction` for additional official pages.
2. **Example fallback** — generate schema from documented Tier A/B examples and mark inferred fields with `x-inferred-from: example`.
3. **Reduced scope** — exclude missing elements from the spec (`out_of_scope`) and generate only the sourced contract.
4. **Stop** — keep `pipeline/openapi/readiness-report.md` only; do not write `pipeline/openapi/openapi.yaml`.

Do not proceed with option 2 or 3 without explicit user approval.

## Workflow

1. **Intake** — material root, profile A/B, scope, strictness (`strict` unless user already approved option 2)
2. **Inventory** — list evidence files with tier, `source_url` if known, role
3. **Preflight** — run Readiness Checklist against Tier A/B only; apply gate rules matching current strictness and scope
4. **Gate** — **GO** | **NO-GO** | **GO (example-fallback)** | **GO (reduced-scope)** per Readiness Checklist gate rules
5. **If NO-GO** — write the four numbered user options and stop
6. **User option follow-up** (only after explicit user reply with option number):
   - **Option 1** — run `strict-api-extraction` for missing official pages; restart from step 1
   - **Option 2** — set `strictness: example-fallback`; write `## User Decision Applied`; re-run steps 3–4 with example-fallback gate rules
   - **Option 3** — write `## User Decision Applied`; for each blocking gap, mark checklist row `out_of_scope`, update Summary scope, and exclude that path/operation/element from assembly; re-run steps 3–4 (strict gate on reduced scope only); on **GO (reduced-scope)**, set `x-readiness: reduced-scope` and `x-readiness-notes` on the spec
   - **Option 4** — stop; keep `pipeline/openapi/readiness-report.md` only
7. **Assemble** — only when gate is **GO**, **GO (example-fallback)**, or **GO (reduced-scope)** — merge in order: pinned complete openapi.json → embedded OpenAPI fragments in markdown → field-level extraction; enrich auth/errors from cross-ref pages; omit `out_of_scope` paths/elements
8. **Annotate** — add `x-source-evidence` on operations, parameters, schemas; add `x-inferred-from: example` on every example-derived schema element
9. **Validate** — valid OpenAPI 3.x; no element without evidence
10. **Deliver** — `pipeline/openapi/readiness-report.md`; `pipeline/openapi/openapi.yaml` only on **GO**, **GO (example-fallback)**, or **GO (reduced-scope)**

Load `references/readiness-report-template.md` before writing the report.

## Assembly Rules

- Start from the highest-tier complete fragment when present (e.g. embedded OpenAPI in endpoint markdown).
- Do not copy example JSON types into schema in `strict` mode.
- In `example-fallback`, infer only fields present in Tier A/B examples and add `x-inferred-from: example` plus `x-source-evidence`.
- Do not fill empty official schema objects from examples in strict mode.
- Pin `openapi` version field to `3.0.x` or `3.1.x` matching source; normalize to valid OpenAPI 3.x.
- Include only in-scope paths; document excluded paths as `out_of_scope` in report.
- After option 3, do not include `out_of_scope` operations, parameters, or response statuses in `pipeline/openapi/openapi.yaml`.

## No-Guess

Forbidden without Tier A/B text: infer types from examples; invent enums; assume required/optional; add status codes; use SDK or third-party specs; use training data.

| Excuse → Reality |
| --- |
| "Extraction report says GO" → extraction GO ≠ schema GO; re-run checklist on Tier A/B |
| "Example shows string" → examples ≠ schema in strict mode; ask before `example-fallback` |
| "Partial openapi has empty properties" → missing, not inferrable |

**STOP:** writing `pipeline/openapi/openapi.yaml` before schema Gate **GO**, **GO (example-fallback)**, or **GO (reduced-scope)**; citing report without `path:line`; silently filling missing schema properties.

## Deliverables

| Schema Gate | Files |
| --- | --- |
| **GO** | `pipeline/openapi/openapi.yaml`, `pipeline/openapi/readiness-report.md`, optional `pipeline/openapi/evidence-map.yaml` |
| **GO (example-fallback)** | `pipeline/openapi/openapi.yaml` with `x-inferred-from: example`, `pipeline/openapi/readiness-report.md` |
| **GO (reduced-scope)** | `pipeline/openapi/openapi.yaml` for reduced scope only, `pipeline/openapi/readiness-report.md` with `out_of_scope` rows |
| **NO-GO** | `pipeline/openapi/readiness-report.md` only — gaps + the four numbered user options; do not delete an existing `pipeline/openapi/openapi.yaml` from a prior run |

After **GO**, suggest `api-client-generator` (generic) or `typed-sdk-from-openapi` (Go) for client work.

## Runtime Validation

After assembling deliverables (workflow step 9), verify the **run output** — not fixture goldens:

- `pipeline/openapi/openapi.yaml` (if written) is valid OpenAPI 3.x
- Every in-scope element has Tier A/B `x-source-evidence` with `path:line`
- Example-derived fields carry `x-inferred-from: example`
- No undocumented fields, types, enums, or status codes were invented
- `pipeline/openapi/readiness-report.md` matches the actual schema gate and deliverables

Do **not** run `validate-readiness-output.sh` against a real API run unless you intentionally compare to a fixture `expected-readiness.yaml`.

## Fixture Tests

Maintainers only — see `references/fixture-tests.md`. All test scripts and fixtures live under `test/` (gitignored; not installed with the skill).

## References

- Readiness report template: `references/readiness-report-template.md`
- Evidence extensions: `references/evidence-extensions.md`
- Fixture tests (maintainers): `references/fixture-tests.md`
