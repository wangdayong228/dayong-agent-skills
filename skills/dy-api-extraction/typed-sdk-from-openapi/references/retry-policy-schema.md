# retry-policy.yaml Schema (v1)

```yaml
version: 1
defaults:
  unlisted: non_retryable   # retryable | non_retryable

operations:
  <operationId>:
    method: GET
    path: /api/example
    policy: retryable       # retryable | non_retryable | idempotent_key_required | unreviewed
    idempotency_header: ""  # required when policy is idempotent_key_required
    reason: "human-readable justification"
    confirmed: false        # true only after user batch approval
```

## Rules

- Every in-scope OpenAPI operation must appear under `operations`.
- SDK Gate **GO** requires `confirmed: true` and `policy != unreviewed` for all operations.
- `retryable` on POST/PATCH/DELETE requires override reason recorded in sdk-readiness-report.
