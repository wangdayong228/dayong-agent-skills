---
name: typed-sdk-from-openapi
description: Use when a pinned OpenAPI 3.x spec exists and a Go typed SDK with confirmed idempotency-aware retry policy is needed. Use after openapi-from-sources schema Gate GO. Do NOT crawl docs or assemble OpenAPI here. Do NOT hand-edit generated SDK files.
---

# Typed SDK From OpenAPI

## Core Rule

Generate a **Go typed SDK** from pinned `schema/openapi.yaml`: raw `oapi-codegen` output plus a refined `pkg/client/` facade. Retry behavior comes from a **user-confirmed** `sdk/retry-policy.yaml` registry — never guess idempotency for write operations.

**Violating the letter of these rules is violating the spirit of these rules.**

## When to Use / NOT

**Use:** `schema/openapi.yaml` exists with upstream schema Gate **GO**; user needs Go client with readable API and controlled retries.

**NOT:** need to crawl docs → `strict-api-extraction`; need schema assembly → `openapi-from-sources`; TypeScript/other languages → out of scope for v1; retry policy undecided and user unavailable for batch review.

## Scope Boundary

Upstream schema Gate **GO** does **not** auto-approve SDK Gate **GO**. Retry policy must be batch-reviewed and confirmed before refined SDK delivery.

Deliver **sdk-readiness report** always. Deliver **full SDK tree** only on SDK Gate **GO**.

## Prerequisites

| Tool | Required | Role |
| --- | --- | --- |
| `oapi-codegen` v2 | **Yes** | Raw client/types generation |
| Go 1.22+ | **Yes** | Refined SDK module |
| PyYAML (via `scripts/bootstrap-python.sh`) | **Yes** | Draft/validate retry-policy |

## Target Layout (Run Directory)

```text
schema/openapi.yaml
sdk/retry-policy.draft.yaml
sdk/retry-policy.yaml
docs/sdk-readiness-report.md
generated/                    # oapi-codegen — never hand-edit
internal/transport/             # RetryPolicyRoundTripper + typed errors
pkg/client/                     # refined public API
scripts/regen.sh
go.mod
```

Default: **commit** `generated/` for reviewable regen diffs.

## Retry Policy Registry

Independent from OpenAPI. Draft with:

```bash
./skills/dy-api-extraction/typed-sdk-from-openapi/scripts/draft-retry-policy.sh \
  schema/openapi.yaml sdk/retry-policy.draft.yaml
```

Schema: `references/retry-policy-schema.md`

| Policy | Runtime behavior |
| --- | --- |
| `retryable` | Retry 429/502/503/504 + transient network errors (max 3, backoff+jitter) |
| `non_retryable` | Single attempt |
| `idempotent_key_required` | Retry only when configured header present |
| `unreviewed` | Blocks SDK Gate |

**Safe default:** unlisted operation → `non_retryable`.

## Interactive Batch Confirmation

After drafting, present:

```markdown
## Retry Policy Review Required

| Operation | Method | Path | Suggested | Reason |
|-----------|--------|------|-----------|--------|

Reply **"approve all"** or overrides: `OperationId → policy [header]`
```

On approval, write `sdk/retry-policy.yaml` with `confirmed: true` on every operation.

Write operations suggested as `non_retryable` — changing to `retryable` requires explicit user override recorded in report.

## SDK Gate

**GO** when all true:

- Every in-scope operation confirmed in `sdk/retry-policy.yaml`
- No `policy: unreviewed`
- User explicitly approved batch
- `go test ./...` passes

**NO-GO:** deliver `docs/sdk-readiness-report.md` + `sdk/retry-policy.draft.yaml` only.

## Workflow

1. **Intake** — confirm `schema/openapi.yaml`, record spec SHA256 and upstream gate mode
2. **Preflight** — inventory operations, auth, servers; start report from `references/sdk-readiness-report-template.md`
3. **Draft policy** — run `draft-retry-policy.sh`
4. **User review** — batch table; write confirmed `sdk/retry-policy.yaml`
5. **Gate** — **GO** or **NO-GO**
6. **Codegen** — `scripts/regen-generated.sh` → `generated/`
7. **Transport** — `internal/transport/` with operation ID via `WithOperationID(ctx, id)`
8. **Refine** — `pkg/client/` per `references/refined-client-patterns.md`
9. **Validate** — `validate-sdk-readiness.sh` + `go test ./...`
10. **Deliver** — per gate table below

## Codegen

```bash
./skills/dy-api-extraction/typed-sdk-from-openapi/scripts/regen-generated.sh /path/to/run-dir
```

Pin oapi-codegen version in report. Never hand-edit `generated/`.

## Transport Seam

Inject retry via owned `http.RoundTripper`, not generated files:

```go
ctx = transport.WithOperationID(ctx, "fr-ohlc-histroy")
resp, err := c.gen.SomeOperationWithResponse(ctx, params)
```

Map non-2xx to typed errors (`AuthError`, `NotFoundError`, `ValidationError`, `RateLimitError`, `ServerError`).

## Deliverables

| SDK Gate | Files |
| --- | --- |
| **GO** | `generated/`, `internal/transport/`, `pkg/client/`, `sdk/retry-policy.yaml`, `docs/sdk-readiness-report.md`, `scripts/regen.sh`, `go.mod` |
| **NO-GO** | `docs/sdk-readiness-report.md`, `sdk/retry-policy.draft.yaml` |

## Verification

```bash
./skills/dy-api-extraction/typed-sdk-from-openapi/scripts/validate-sdk-readiness.sh \
  /path/to/run-dir \
  skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/expected/retry-policy.yaml

go test ./...
```

Offline fixture (when present locally):

```bash
./skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/verify.sh
```

## No-Guess (Retry)

| Excuse → Reality |
| --- |
| "GET is probably safe" → still requires user batch confirm before SDK Gate **GO** |
| "OpenAPI lacks idempotency" → default write ops to `non_retryable`, not `retryable` |
| "I'll add retry in generated code" → forbidden; use transport layer |

**STOP:** delivering `pkg/client/` before confirmed retry-policy; retrying POST without explicit user override; editing `generated/`.

## References

- Retry policy schema: `references/retry-policy-schema.md`
- SDK report template: `references/sdk-readiness-report-template.md`
- Refined client patterns: `references/refined-client-patterns.md`
- Transport principles: `api-client-generator` (global skill)

## Pipeline

Upstream: `openapi-from-sources` → **this skill** → consumer application.
