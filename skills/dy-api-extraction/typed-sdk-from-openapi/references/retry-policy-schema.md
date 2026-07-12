# retry-policy.yaml Schema (v1)

```yaml
version: 1
defaults:
  unlisted: non_retryable

operations:
  <operationId>:
    method: GET
    path: /api/example
    policy: retryable          # retryable | non_retryable | idempotent_key_required | unreviewed
    idempotency_header: ""     # required when policy=idempotent_key_required
    reason: "human-readable evidence"
    confirmed: false
```

## Draft Rules

- GET/HEAD/OPTIONS -> `retryable`
- POST/PUT/PATCH/DELETE -> `non_retryable` by default
- `x-idempotent: true` -> `retryable` (still needs user confirmation)
- Explicit idempotency header in parameters -> `idempotent_key_required` + header name
- Missing evidence or unclear semantics -> `unreviewed`

If `operationId` is absent, derive a stable ID from `method + path` and record that derivation in `.sdkgen/sdk-readiness-report.md`.

## Gate Rules

SDK Gate can be GO only when:

- every in-scope operation appears in `operations`
- every operation has `confirmed: true`
- no operation has `policy: unreviewed`

Any violation is NO-GO fail-fast.

## Policy Semantics

- `retryable`: retry transient transport errors and HTTP `429/502/503/504`
- `non_retryable`: single attempt
- `idempotent_key_required`: retry only when required header is present
- `unreviewed`: blocks delivery

## Safe Defaults

- Unlisted operations resolve to `non_retryable`
- Write methods are never upgraded to `retryable` without explicit user approval
