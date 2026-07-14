# typed-sdk-from-openapi Design Spec

> Status: approved for implementation planning (2026-07-12)
> Pipeline position: `strict-api-extraction` → `openapi-from-sources` → **typed-sdk-from-openapi**

## Goal

Add a repo-local Agent Skill that generates a **Go typed SDK** from a pinned OpenAPI 3.x spec:

1. **Raw SDK** — `oapi-codegen` output treated as a build artifact (never hand-edited).
2. **Refined SDK** — hand-written `pkg/client/` facade with precise types, readable domain API, and maintainable boundaries.
3. **Retry policy** — idempotency-aware retries via an explicit, user-confirmed `retry-policy.yaml` registry; state-changing writes default to no retry.

## Non-Goals

- Doc crawling or schema assembly (upstream: `strict-api-extraction`, `openapi-from-sources`).
- Multi-language codegen in v1 (Go only).
- Pagination/sync engines.
- Hand-editing generated files or post-codegen patches.

## Architecture

**Recommended approach: Transport-layer unified retry (Option 1).**

```
schema/openapi.yaml
       │
       ├─► draft retry-policy.draft.yaml ──► user batch review ──► retry-policy.yaml
       │
       ├─► oapi-codegen ──► generated/          (build artifact, regen only)
       │
       ├─► internal/transport/                  (RetryPolicyRoundTripper + typed errors)
       │
       └─► pkg/client/                          (refined public SDK)
```

Principles aligned with `api-client-generator`:

- Pin spec by path + SHA256 hash.
- Inject resilience via owned transport, not generated code edits.
- Export one configured client instance for consumers.

## Global Constraints

- **Language:** Go; codegen tool `oapi-codegen` v2.
- **Input:** `schema/openapi.yaml` from upstream with schema Gate **GO** (strict or user-approved example-fallback).
- **Generated code:** committed, reproducible, never hand-edited.
- **Public API:** only `pkg/client/` is exported to consumers; `generated/` is internal.
- **Retry default:** unlisted or unreviewed operations → **non_retryable** at runtime.
- **Retry confirmation:** batch interactive review required before SDK Gate **GO**; no refined SDK without confirmed policy.
- **Retriable status codes:** 429, 502, 503, 504 + transient network errors.
- **Retry budget:** max 3 attempts, exponential backoff with full jitter.
- **Write safety:** POST/PATCH/DELETE/PUT draft suggestions default to `non_retryable`; changing to `retryable` requires explicit user override with documented reason.

## Skill Location & Files

```
skills/dy-api-extraction/typed-sdk-from-openapi/
  SKILL.md
  references/
    retry-policy-schema.md
    sdk-readiness-report-template.md
    refined-client-patterns.md
  scripts/
    draft-retry-policy.py          # openapi → retry-policy.draft.yaml
    validate-sdk-readiness.sh      # gate checks
    regen-generated.sh             # oapi-codegen wrapper
  agents/
    openai.yaml                    # optional agent metadata (match sibling skills)
  test/
    coinglass-fr-ohlc-history/
      SCENARIO.md
      fixture-input/
        schema/openapi.yaml        # from openapi-from-sources example-fallback output
      expected/
        sdk-readiness-report.md
        retry-policy.yaml
      verify.sh
```

## Target Project Layout (Run Directory)

Produced in the user's target project (or skill test run dir):

```
schema/openapi.yaml
sdk/
  retry-policy.draft.yaml
  retry-policy.yaml
docs/
  sdk-readiness-report.md
generated/                         # oapi-codegen output
internal/
  transport/
    retry.go
    errors.go
    retry_test.go
pkg/
  client/
    client.go
    funding_rate.go                # domain files as needed
    client_test.go
scripts/
  regen.sh
go.mod
go.sum
```

Add `generated/` to `.gitignore` only if the project prefers regen-at-build; default for this skill: **commit generated/** for reviewable diffs (consistent with `api-client-generator`).

## Workflow

### 1. Intake

- Confirm material root and `schema/openapi.yaml` exist.
- Record: OpenAPI version, operation count, spec SHA256, upstream schema gate mode.
- If no pinned spec → **NO-GO** (suggest `openapi-from-sources`).

### 2. Preflight

- Parse all operations; require unique `operationId` (generate stable fallback from method+path if missing, record in report).
- Inventory parameters, auth scheme, servers URL.
- Write initial `docs/sdk-readiness-report.md` preflight section.

### 3. Draft Retry Policy

Run `scripts/draft-retry-policy.py schema/openapi.yaml sdk/retry-policy.draft.yaml`.

Draft rules:

| Condition | Suggested policy |
|-----------|------------------|
| GET, HEAD, OPTIONS | `retryable` |
| POST, PATCH, DELETE, PUT | `non_retryable` |
| OpenAPI `x-idempotent: true` on operation | `retryable` (still needs user confirm) |
| Documented idempotency header in operation parameters | `idempotent_key_required` + header name |
| Ambiguous (e.g., PUT without idempotency evidence) | `unreviewed` |

Each entry includes `reason` citing method, path, and any spec evidence.

### 4. Interactive Batch Confirmation

Present summary table to user:

```markdown
## Retry Policy Review Required

| Operation | Method | Path | Suggested | Reason |
|-----------|--------|------|-----------|--------|
| GetFundingRateHistory | GET | /api/futures/funding-rate/history | retryable | read-only GET |

Reply **"approve all"** or list overrides:
`OperationName → policy [header]`
```

On approval:

- Write confirmed `sdk/retry-policy.yaml` (version 1 schema).
- Mark each operation `confirmed: true` with `confirmed_at` timestamp in report metadata.

### 5. SDK Gate

**GO** when all true:

- Every in-scope operation has a confirmed entry in `retry-policy.yaml`.
- No entry has `policy: unreviewed`.
- User explicitly approved the batch (record approval in report).

**NO-GO** otherwise:

- Deliver `docs/sdk-readiness-report.md` + `sdk/retry-policy.draft.yaml`.
- Do not write `pkg/client/` production code (stub/template allowed in report appendix only).

### 6. Codegen (Raw SDK)

`scripts/regen-generated.sh`:

```bash
oapi-codegen -generate types,client -package generated \
  -o generated/client.gen.go schema/openapi.yaml
```

Pin command + oapi-codegen version in report and `scripts/regen.sh`.

### 7. Transport Layer

`internal/transport/retry.go` implements `http.RoundTripper`:

- Lookup policy by operation ID passed via request context (`transport.WithOperationID(ctx, id)`).
- `retryable`: retry on 429/502/503/504 and net.Error temporary failures; honor `Retry-After` when present.
- `non_retryable`: single attempt.
- `idempotent_key_required`: retry only if configured header present on request.
- Map non-2xx to typed errors in `errors.go`: `AuthError`, `NotFoundError`, `ValidationError`, `RateLimitError`, `ServerError`.

Refined client and generated client must attach operation ID to every outbound request context.

### 8. Refined SDK (`pkg/client/`)

Hand-written facade rules:

- Constructor: `New(cfg Config) (*Client, error)` with base URL, auth, timeout, optional custom HTTP client.
- Domain method names (e.g., `FundingRateHistory(ctx, params)` not generated names).
- Narrow parameter/result structs; map from generated types internally.
- Do not re-export generated package types in public signatures where avoidable.
- Document which methods are retryable in Go doc comments (mirror registry).

### 9. Validate

```bash
./skills/dy-api-extraction/typed-sdk-from-openapi/scripts/validate-sdk-readiness.sh \
  /path/to/run-dir \
  skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/expected/retry-policy.yaml
go test ./...
```

Transport tests (required):

- `retryable` operation retries on 503 then succeeds.
- `non_retryable` operation does not retry on 503.
- `idempotent_key_required` retries only when header set.

### 10. Deliver

| SDK Gate | Files |
|----------|-------|
| **GO** | `generated/`, `internal/transport/`, `pkg/client/`, `sdk/retry-policy.yaml`, `docs/sdk-readiness-report.md`, `scripts/regen.sh`, `go.mod` |
| **NO-GO** | `docs/sdk-readiness-report.md`, `sdk/retry-policy.draft.yaml` |

## retry-policy.yaml Schema (v1)

```yaml
version: 1
defaults:
  unlisted: non_retryable

operations:
  GetFundingRateHistory:
    method: GET
    path: /api/futures/funding-rate/history
    policy: retryable          # retryable | non_retryable | idempotent_key_required | unreviewed
    idempotency_header: ""     # required when policy is idempotent_key_required
    reason: "read-only GET"
    confirmed: true
```

Forbidden without user confirmation: `policy: retryable` on POST/PATCH/DELETE unless user override recorded in report.

## SDK Readiness Report

Template: `references/sdk-readiness-report-template.md`

Sections:

1. Run metadata (spec hash, oapi-codegen version, operation count)
2. Preflight checklist (operationId, auth, servers)
3. Retry policy review status (confirmed / pending / overrides)
4. SDK Gate verdict (**GO** / **NO-GO**)
5. Deliverables list
6. Regen instructions

## Pipeline Integration

Update `openapi-from-sources/SKILL.md` deliverables section:

- After schema Gate **GO**, suggest `typed-sdk-from-openapi` (not generic `api-client-generator`) for Go client work in this pipeline.
- Keep `api-client-generator` as conceptual reference for transport principles.

## Testing Strategy

### Offline fixture: coinglass-fr-ohlc-history

Reuse openapi-from-sources example-fallback output for `GET /api/futures/funding-rate/history`:

1. `verify.sh` runs draft-retry-policy, validates against golden `retry-policy.yaml`.
2. Assert SDK Gate **GO** with confirmed golden policy.
3. Run `go test ./...` in fixture module.
4. Assert `pkg/client` compiles and exposes refined method for the endpoint.

### Agent live run (optional)

Same material root as openapi-from-sources fixture; output to temp dir; run validate script.

## Error Handling & Edge Cases

| Case | Behavior |
|------|----------|
| Missing operationId | Derive stable ID; flag in report; use derived ID in registry |
| Spec updated after policy confirm | Re-run draft; diff report; require re-confirmation for changed ops |
| 429 with Retry-After | Wait specified duration (cap 60s) before retry |
| Context canceled | No retry; return ctx.Err() |
| Partial scope | Only in-scope operations need registry entries; document excluded paths |

## Security

- Never retry authenticated write operations unless explicitly confirmed.
- Do not log auth headers or idempotency keys.
- Typed errors must not leak raw response bodies into success paths.

## Success Criteria

1. Skill document enables an agent to produce raw + refined Go SDK from pinned OpenAPI.
2. Retry behavior matches confirmed registry in unit tests.
3. Offline `verify.sh` passes in CI without network.
4. Regenerating from updated spec produces reviewable diff with zero manual reconciliation in generated/.

## Open Questions (resolved)

| Question | Decision |
|----------|----------|
| New skill vs extend api-client-generator | Repo-local pipeline skill (B) |
| Language | Go + oapi-codegen |
| Retry policy source | Independent registry + interactive batch confirm (C) |
| Architecture | Transport-layer unified retry |
