# Transport Patterns (Go)

## Purpose

`internal/transport/` is the transport seam owned by hand-written code. It centralizes cross-cutting HTTP behavior without editing generated files.

## Why Internal

Keep transport logic under `internal/transport/` so external consumers cannot import it directly. Public consumers should only use `pkg/client`.

## Required Capabilities

1. Timeout and context deadlines
2. Authentication and default headers
3. Typed error mapping for non-2xx responses
4. Retry policy lookup by policy operation key
5. Optional request/response logging hooks

## Operation Key Context Contract

`pkg/client` must attach the **policy operation key** (not an ad-hoc label) before calling generated client methods. The key must match an entry in `<output>/sdk/retry-policy.yaml` `operations`:

- Use OpenAPI `operationId` when present
- Otherwise use the derived key from `references/retry-policy-schema.md` (`{UPPERCASE_METHOD}_{path_without_leading_slash_with_slashes_as_underscores}`, path template literals preserved)

```go
// operationId present in spec:
ctx = transport.WithOperationID(ctx, "getFundingRateHistory")

// operationId absent; derived GET /api/v1/funding-rate/history:
ctx = transport.WithOperationID(ctx, "GET_api_v1_funding-rate_history")
resp, err := c.gen.GetFundingRateHistoryWithResponse(ctx, params)
```

Transport reads this key to apply retry rules from `<output>/sdk/retry-policy.yaml`.

## Typed Error Contract

Map HTTP failures to typed categories:

- `AuthError` for 401/403
- `NotFoundError` for 404
- `ValidationError` for 422
- `RateLimitError` for 429
- `ServerError` for 5xx

Never return a success-shaped object for non-2xx responses.

## Retry Contract

Retry only when policy allows and error/status is transient:

- statuses: `429`, `502`, `503`, `504`
- transient network errors

Write methods default to `non_retryable` unless user-confirmed override.

## Injection Pattern

Generated client must receive a custom `http.Client` configured with the transport chain. Do not patch generated code.

## Do NOT

- Do NOT hand-edit `generated/`
- Do NOT scatter auth/header logic in endpoint methods
- Do NOT hardcode retry decisions in generated methods
