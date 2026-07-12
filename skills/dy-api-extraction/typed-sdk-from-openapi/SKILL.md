---
name: typed-sdk-from-openapi
description: Use when a trusted pinned OpenAPI 3.x spec exists and a clean two-layer Go SDK is needed. Always invoke api-client-generator first for raw codegen/transport seam, then build refined pkg/client with retry-policy confirmation gate. Do NOT crawl docs or assemble OpenAPI here.
---

# Typed SDK From OpenAPI (Go)

## Core Rule

Input is a trusted pinned OpenAPI 3.x spec from any source. First run the `api-client-generator` workflow to produce raw generated SDK plus transport seam baseline, then deliver a clean two-layer Go SDK module: `generated/` (raw) + `pkg/client/` (refined API), with retry policy confirmed by the user.

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
- `go test ./...` passes in `<output>/`

Otherwise **NO-GO**.

## Workflow

1. **Invoke api-client-generator first** (mandatory)
2. **Preflight**: validate spec trust/pinning/OpenAPI 3.x; record SHA256 to `.sdkgen/`
3. **Draft retry policy**: write `.sdkgen/retry-policy.draft.yaml` per `references/retry-policy-schema.md`
4. **User review**: batch table + `approve all` or explicit overrides
5. **Gate check**: GO or NO-GO
6. **Phase A (raw)**: generate `generated/client.gen.go` via `oapi-codegen`
7. **Phase B (refined)**: implement `internal/transport/` and `pkg/client/`
8. **Copy/normalize spec** into `<output>/schema/openapi.yaml`
9. **Write regen script** `<output>/scripts/regen.sh`
10. **Validate**: structure checks + `go test ./...`
11. **Deliver**: clean `<output>/`; keep `.sdkgen/` outside deliverable

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
