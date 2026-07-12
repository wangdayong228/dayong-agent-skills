# SDK Readiness Report

## Run Metadata

- input_spec_path:
- normalized_spec_path: `<output>/schema/openapi.yaml`
- spec_sha256:
- openapi_version:
- operation_count:
- generation_time:
- optional_upstream:

## Input Trust Check

| Check | Status | Notes |
| --- | --- | --- |
| OpenAPI 3.x | | |
| pinned/fixed source | | |
| trusted source provenance | | |
| parseable schema | | |

## Retry Policy Review

- draft_policy_path: `.sdkgen/retry-policy.draft.yaml`
- confirmed_policy_path: `<output>/sdk/retry-policy.yaml`
- review_mode: `approve all` or overrides
- overrides:

| Operation | Method | Path | Suggested | Final | Confirmed |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## Gate Result

**SDK Gate:** GO | NO-GO

**NO-GO reason (required when NO-GO):**

- 

## Final Output Checklist (GO only)

- [ ] `<output>/schema/openapi.yaml`
- [ ] `<output>/generated/client.gen.go`
- [ ] `<output>/internal/transport/`
- [ ] `<output>/pkg/client/`
- [ ] `<output>/sdk/retry-policy.yaml`
- [ ] `<output>/scripts/regen.sh`
- [ ] `<output>/go.mod`
- [ ] `go test ./...` passed
- [ ] final output excludes `.sdkgen/`

## Regen Command

```bash
./scripts/regen.sh
go test ./...
```

## Delivery Notes

- `.sdkgen/` contains intermediate artifacts only and is not part of final SDK deliverable.
