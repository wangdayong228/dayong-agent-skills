# Refined Go Client Patterns

## Module layout

- `generated/` — oapi-codegen output; never import from outside module except internal adapters.
- `internal/transport/` — RoundTripper, typed errors, operation context.
- `pkg/client/` — only public API.

## Constructor

```go
func New(cfg Config) (*Client, error)
```

## Naming

- Prefer domain names: `FundingRateHistory` over `GetApiFuturesFundingRateHistory`.
- Use parameter structs: `FundingRateHistoryParams`.

## Operation context (required for retry lookup)

```go
ctx = transport.WithOperationID(ctx, "GetFundingRateHistory")
```

## Do NOT

- Re-export generated types in public method signatures when mappable.
- Patch generated files.
