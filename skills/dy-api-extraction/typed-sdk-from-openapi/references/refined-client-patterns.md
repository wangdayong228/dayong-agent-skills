# Refined Client Patterns (Go)

## Layering

- `generated/`: raw `oapi-codegen` output, never edited
- `internal/transport/`: retry/auth/error plumbing
- `pkg/client/`: public refined API consumed by applications

## Constructor Pattern

Expose a single constructor with centralized config:

```go
func New(cfg Config) (*Client, error)
```

`Config` should include:

- Base URL
- Auth token/provider
- Default headers
- Timeout
- Retry policy path or in-memory policy object

## Naming Pattern

- Prefer business names over generated names
- Use domain-focused method names and parameter structs

Example:

- Prefer `FundingRateHistory` over `GetApiV1FuturesFundingRateHistory`
- Prefer `FundingRateHistoryParams` over long generated signatures

## Public API Rules

- `pkg/client` should hide generated naming noise
- Avoid re-exporting generated types unless mapping is expensive or lossy
- Keep public errors typed and branchable

## Call Flow

`pkg/client` method -> attach policy operation key (`WithOperationID`) -> call generated method -> **normalize HTTP status/body to typed errors** (not in RoundTripper) -> return domain result.

## Do NOT

- Do NOT let call sites import `generated/` directly
- Do NOT leak transport internals as public API
- Do NOT bypass policy operation key context in refined methods
