---
name: typed-sdk-from-openapi
description: Use when a trusted pinned OpenAPI 3.x spec exists and a clean two-layer Go SDK is needed. Run preflight and dependency checks first, load api-client-generator guidance, then complete retry-policy draft/review/confirmation gate before Phase A/B codegen. Do NOT crawl docs or assemble OpenAPI here.
---

# Typed SDK From OpenAPI (Go)

## Core Rule

Input is a trusted pinned OpenAPI 3.x spec from any source. Run preflight gate and dependency check first, then load/apply `api-client-generator` guidance (without running codegen yet), complete retry policy draft/review/confirmation gate, and only then produce the clean two-layer Go SDK module: `generated/` (raw) + `pkg/client/` (refined API).

`internal/transport/` is part of the refined layer implementation and must stay internal.

**Violating the letter of these rules is violating the spirit of these rules.**

## When to Use / NOT

**Use:**

- User already has a trusted pinned OpenAPI 3.x file (`openapi.yaml|json`, `schema/openapi.yaml|json`)
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

## Input Requirements

Accepted inputs:

```text
schema/openapi.yaml
schema/openapi.json
openapi.yaml
openapi.json
```

Requirements:

- Must be OpenAPI 3.x
- Must be pinned (fixed file/version/hash) and recorded by SHA256
- If not trusted/pinned/3.x, write `.sdkgen/sdk-readiness-report.md` and stop with **NO-GO**

## Output Model

### Final Output Module (clean deliverable)

```text
<output>/
  schema/openapi.yaml
  generated/client.gen.go
  internal/transport/{transport.go,errors.go,operation.go,retry.go}
  pkg/client/client.go
  sdk/spec-manifest.yaml
  sdk/retry-policy.yaml
  scripts/regen.sh
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

If SDK Gate is NO-GO, only write `.sdkgen/sdk-readiness-report.md` (and draft retry policy when available), then stop. Do not write SDK code outputs.

## SDK Gate

**GO** only when all true:

- Retry policy is confirmed by user for all in-scope operations
- No `policy: unreviewed`
- Final output module structure is complete
- `<output>/sdk/spec-manifest.yaml` records spec SHA256 provenance
- `go test ./...` passes in `<output>/`

Otherwise **NO-GO**.

## Workflow

1. **Preflight gate first**: validate spec trust/pinning/OpenAPI 3.x and record SHA256 to `.sdkgen/`; if fail, NO-GO and stop before codegen
2. **Check dependency**: confirm `api-client-generator` capability is available; if missing, NO-GO and stop
3. **Invoke api-client-generator guidance** and apply its constraints in subsequent generation/transport steps (mandatory dependency; do not run codegen before policy gate)
4. **Draft retry policy**: write `.sdkgen/retry-policy.draft.yaml` per `references/retry-policy-schema.md`
5. **User review**: batch table + `approve all` or explicit overrides
6. **Policy gate**: if any operation is unconfirmed or `unreviewed`, NO-GO and stop before deliverable
7. **Phase A (raw)**: generate `generated/client.gen.go` via `oapi-codegen`
8. **Phase B (refined)**: implement `internal/transport/` and `pkg/client/`
9. **Copy/normalize spec** into `<output>/schema/openapi.yaml`
10. **Write spec manifest** at `<output>/sdk/spec-manifest.yaml` with spec path + SHA256 + generation timestamp
11. **Write regen script** `<output>/scripts/regen.sh`
12. **Final SDK gate**: validate structure checks + `go test ./...`; then decide GO/NO-GO
13. **Deliver**: clean `<output>/`; keep `.sdkgen/` outside deliverable

## Transport Rules

Use `http.RoundTripper` in `internal/transport/` for:

- Timeout and context deadline handling
- Auth and default headers
- Non-2xx to typed errors (401/403, 404, 422, 429, 5xx)
- Retry lookup by operation ID (`WithOperationID(ctx, opID)`)

Never patch generated files to add these policies.

## Retry Policy Defaults

- GET/HEAD/OPTIONS -> `retryable`
- POST/PUT/PATCH/DELETE -> `non_retryable` unless explicit evidence/override
- `x-idempotent: true` -> `retryable` (still needs user confirmation)
- Idempotency header evidence -> `idempotent_key_required`
- Unknown/ambiguous -> `unreviewed` (blocks GO)

## Runtime Validation

Before claiming completion:

- `<output>/schema/openapi.yaml` exists
- `<output>/generated/client.gen.go` exists and is generated-only
- `<output>/internal/transport/` and `<output>/pkg/client/` exist and compile
- `<output>/sdk/spec-manifest.yaml` exists and includes OpenAPI SHA256 provenance
- `<output>/sdk/retry-policy.yaml` has confirmed operations and no `unreviewed`
- `<output>/scripts/regen.sh` reproduces generated layer
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
