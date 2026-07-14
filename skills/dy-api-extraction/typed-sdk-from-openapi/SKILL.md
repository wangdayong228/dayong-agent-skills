---
name: typed-sdk-from-openapi
description: Use when a trusted pinned OpenAPI 3.x spec exists and a clean two-layer Go SDK is needed. Run preflight and dependency checks first, load api-client-generator guidance, then complete retry-policy draft/review/confirmation gate before Phase A/B codegen. Do NOT crawl docs or assemble OpenAPI here.
---

# Typed SDK From OpenAPI (Go)

## Core Rule

Input is a trusted pinned OpenAPI 3.x spec from any source. Prefer `pipeline/openapi/openapi.yaml`; an explicit user-pinned OpenAPI 3.x path is also valid. Run preflight gate and dependency check first, then load/apply `api-client-generator` guidance (without running codegen yet), complete retry policy draft/review/confirmation gate, and only then produce the clean two-layer Go SDK module: `internal/generated/` (raw) + `pkg/client/` (refined API).

`internal/transport/` is part of the refined layer implementation and must stay internal.

**Violating the letter of these rules is violating the spirit of these rules.**

## When to Use / NOT

**Use:**

- User already has a trusted pinned OpenAPI 3.x file (prefer `pipeline/openapi/openapi.yaml`; explicit pinned path accepted)
- Target output is a Go SDK with raw + refined layers
- User wants deterministic retry policy review before SDK delivery

**NOT:**

- Need to crawl docs or collect source pages -> `strict-api-extraction`
- Need to reconstruct OpenAPI from materials -> `openapi-from-sources`
- Spec is untrusted, floating, or non-OpenAPI 3.x (fail-fast with report)
- Non-Go SDK generation

## Scope Boundary

This skill does not generate or repair OpenAPI specs. It consumes an existing trusted spec and builds SDK outputs only.

`openapi-from-sources` is an optional upstream, not a prerequisite.

## Dependency Prerequisite

This skill requires `api-client-generator` capability in the environment. If unavailable, stop with NO-GO and record the missing dependency in `.sdkgen/sdk-readiness-report.md`.

When any confirmed operation uses `retryable` or `idempotent_key_required`, also require `rate-limit-handler` capability (backoff/jitter/Retry-After). If missing, stop with NO-GO before Phase B.

### api-client-generator vs retry-policy boundary

`api-client-generator` owns codegen patterns, transport seam design, and typed error mapping. It defers retry **backoff algorithms** to `rate-limit-handler`.

This skill owns retry **policy** only:

- Draft/review per-operation retry semantics in `.sdkgen/retry-policy.draft.yaml`
- After user confirmation, write the finalized policy to `<output>/config/retry-policy.yaml`
- Enforce policy gate before codegen
- Wire transport retry lookup to confirmed policy keys

Do not let `api-client-generator` override or bypass the retry-policy confirmation gate in this workflow.

## Input Requirements

Accepted inputs:

```text
pipeline/openapi/openapi.yaml          # preferred; must live in the target project
<explicit-user-pinned-openapi-3.x-path>
```

Requirements:

- Must be OpenAPI 3.x
- Must be pinned (fixed file/version/hash) and recorded by SHA256
- If not trusted/pinned/3.x, write `.sdkgen/sdk-readiness-report.md` and stop with **NO-GO**
- For Final SDK Gate **GO** / deliverable packages, the OpenAPI file used by `tools/regen.sh` **must** be inside the target project tree (prefer `pipeline/openapi/openapi.yaml`). An external pin (temp path, sibling repo, absolute path outside `<output>`) is allowed only as a **preflight input**; before writing regen config, copy/normalize it into `pipeline/openapi/openapi.yaml` and record that in-repo path in `config/spec-manifest.yaml`. Do **not** invent a top-level deliverable `schema/openapi.yaml`.

## Output Model

### Final Output Module (clean deliverable)

```text
<output>/
  internal/generated/client.gen.go
  internal/transport/{transport.go,errors.go,operation.go,retry.go}
  pkg/client/client.go
  config/spec-manifest.yaml
  config/retry-policy.yaml
  tools/regen.sh
  tools/oapi-codegen.yaml
  go.mod
  go.sum (optional)
```

### Intermediate Workspace (not deliverable)

```text
.sdkgen/
  retry-policy.draft.yaml
  sdk-readiness-report.md
  preflight-notes.md (optional)
```

`.sdkgen/` must be gitignored in the target project and excluded from final output.

### NO-GO Behavior (fail-fast)

**Preflight, dependency, or policy gate NO-GO** (before Phase A):

- Write `.sdkgen/sdk-readiness-report.md` (and draft retry policy when available)
- Stop before codegen; do not create `<output>/` SDK directories

**Final SDK gate NO-GO** (after Phase A/B):

- Write or update `.sdkgen/sdk-readiness-report.md` with blocking reasons
- Stop before delivery; partial `<output>/` files may exist but are not a completed deliverable

## SDK Gate

**GO** only when all true:

- Retry policy is confirmed by user for all in-scope operations
- No `policy: unreviewed`
- All derived operation keys are unique (no collisions)
- When any operation is `retryable` or `idempotent_key_required`, `rate-limit-handler` capability is available
- Final output module structure is complete
- `<output>/config/spec-manifest.yaml` records input spec path, SHA256 provenance, and generation timestamp
- `go test ./...` passes in `<output>/`

Otherwise **NO-GO**.

## Workflow

1. **Preflight gate first**: validate spec trust/pinning/OpenAPI 3.x and record SHA256 to `.sdkgen/`; if fail, NO-GO and stop before codegen
2. **Check dependency**: confirm `api-client-generator` capability is available; if missing, NO-GO and stop
3. **Invoke api-client-generator guidance** and apply its constraints in subsequent generation/transport steps (mandatory dependency; do not run codegen before policy gate)
4. **Draft retry policy**: write `.sdkgen/retry-policy.draft.yaml` per `references/retry-policy-schema.md`
5. **User review**: batch table + `approve all` or explicit overrides
6. **Policy gate**: if any operation is unconfirmed or `unreviewed`, NO-GO and stop before codegen; if any confirmed operation is `retryable` or `idempotent_key_required`, confirm `rate-limit-handler` capability is available (backoff for `internal/transport/retry.go`), otherwise NO-GO
7. **Write confirmed retry policy** to `<output>/config/retry-policy.yaml` with every in-scope operation `confirmed: true` and no `unreviewed`
8. **Phase A (raw)**: generate `internal/generated/client.gen.go` via `oapi-codegen`
9. **Phase B (refined)**: implement `internal/transport/` and `pkg/client/`
10. **Write spec manifest** at `<output>/config/spec-manifest.yaml` with in-project input spec path + SHA256 + generation timestamp (`input_spec_path` must resolve inside the target project after any external-pin copy into `pipeline/openapi/openapi.yaml`)
11. **Write codegen config and regen script** at `<output>/tools/oapi-codegen.yaml` and `<output>/tools/regen.sh` — both must read the **in-project** OpenAPI from `config/spec-manifest.yaml` `input_spec_path` (typically `pipeline/openapi/openapi.yaml`). Do **not** assume or recreate a deliverable `schema/openapi.yaml`. A clean checkout of the module must be able to re-run `tools/regen.sh` without external paths
12. **Final SDK gate**: validate structure checks + `go test ./...`; then decide GO/NO-GO
13. **Deliver (GO only)**: on GO, deliver clean `<output>/` and keep `.sdkgen/` outside deliverable; on NO-GO, write `.sdkgen/sdk-readiness-report.md` and stop without delivery

## Transport Rules

Use `http.RoundTripper` in `internal/transport/` for:

- Timeout and context deadline handling
- Auth and default headers
- Retry lookup by policy operation key (`WithOperationID(ctx, opKey)`), using the exact key from `<output>/config/retry-policy.yaml` `operations` map (OpenAPI `operationId` when present, otherwise derived per `references/retry-policy-schema.md`)
- Backoff execution via `rate-limit-handler` when policy allows retry

`RoundTripper` must follow the `net/http` contract: return `err == nil` when a response is obtained, regardless of HTTP status.

Normalize non-2xx HTTP responses to typed errors (401/403, 404, 422, 429, 5xx) in `pkg/client/` after the generated call returns the response — not inside `RoundTripper`.

Never patch generated files to add these policies.

## Retry Policy Defaults

- GET/HEAD/OPTIONS -> `retryable`
- POST/PUT/PATCH/DELETE -> `non_retryable` unless explicit evidence/override
- `x-idempotent: true` -> `retryable` (still needs user confirmation)
- Idempotency header evidence -> `idempotent_key_required`
- Unknown/ambiguous -> `unreviewed` (blocks GO)

## Runtime Validation

Before claiming completion:

- Input spec path is recorded in `<output>/config/spec-manifest.yaml` and resolves **inside** the project tree (typically `pipeline/openapi/openapi.yaml`); no deliverable `schema/openapi.yaml` copy is required
- `<output>/internal/generated/client.gen.go` exists and is generated-only
- `<output>/internal/transport/` and `<output>/pkg/client/` exist and compile
- `<output>/config/spec-manifest.yaml` exists and includes input OpenAPI path, SHA256 provenance, and generation timestamp
- `<output>/config/retry-policy.yaml` has confirmed operations and no `unreviewed`
- `<output>/tools/regen.sh` reproduces generated layer using `<output>/tools/oapi-codegen.yaml` against the in-project `input_spec_path`
- `<output>/go test ./...` passes
- Final output excludes `.sdkgen/` intermediates

## References

- Retry policy schema: `references/retry-policy-schema.md`
- SDK readiness report template: `references/sdk-readiness-report-template.md`
- Refined client patterns: `references/refined-client-patterns.md`
- Transport patterns: `references/transport-patterns.md`
- Verification checklist: `references/fixture-tests.md`

## Pipeline

Optional upstream:

`strict-api-extraction` -> `openapi-from-sources` -> **typed-sdk-from-openapi**

Direct input path is also valid:

trusted pinned OpenAPI 3.x -> **typed-sdk-from-openapi**
