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

If `operationId` is absent, derive a collision-safe operation key:

```text
{UPPERCASE_METHOD}_{escaped_path}
```

Escaping rules (apply in order to the path template without its leading slash):

1. Replace each literal `_` with `__`
2. Replace each `/` with `_`

Normalize the HTTP verb to uppercase when deriving from OpenAPI `paths` keys (e.g. `get` -> `GET`).

Use the path template exactly as declared in the OpenAPI `paths` key, including `{param}` placeholders unchanged.

Example: `GET` + `/api/v1/funding-rate/history` -> `GET_api_v1_funding-rate_history`

Example (collision avoided): `GET` + `/foo/bar` -> `GET_foo_bar`; `GET` + `/foo_bar` -> `GET_foo__bar`

Example with template: `GET` + `/users/{userId}` -> `GET_users_{userId}`

After deriving all keys, detect duplicates. Any collision is **NO-GO** — record colliding method/path pairs in `.sdkgen/sdk-readiness-report.md` and require explicit `operationId` overrides before GO.

Quote YAML map keys when the derived key contains characters YAML may parse specially (e.g. `{`, `}`, `:`).

Record any derived keys in `.sdkgen/sdk-readiness-report.md`. Transport and `pkg/client` must use these exact keys with `WithOperationID`.

## Gate Rules

SDK Gate can be GO only when:

- every in-scope operation appears in `operations`
- every operation has `confirmed: true`
- no operation has `policy: unreviewed`
- all derived operation keys are unique (no collisions)

Any violation is NO-GO fail-fast.

## Policy Semantics

- `retryable`: retry transient transport errors and HTTP `429/502/503/504`
- `non_retryable`: single attempt
- `idempotent_key_required`: retry only when required header is present
- `unreviewed`: blocks delivery

## Safe Defaults

- Unlisted operations resolve to `non_retryable`
- Write methods are never upgraded to `retryable` without explicit user approval
