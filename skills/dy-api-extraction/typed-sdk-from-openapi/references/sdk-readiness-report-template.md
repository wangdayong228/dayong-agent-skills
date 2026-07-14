# SDK Readiness Report

## Run Metadata

- input_spec_path:
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
- confirmed_policy_path: `<output>/config/retry-policy.yaml`
- spec_manifest_path: `<output>/config/spec-manifest.yaml`
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

- [ ] `<output>/internal/generated/client.gen.go`
- [ ] `<output>/internal/transport/`
- [ ] `<output>/pkg/client/`
- [ ] `<output>/config/spec-manifest.yaml` records in-project `input_spec_path` + SHA256 (typically `pipeline/openapi/openapi.yaml`; no deliverable `schema/openapi.yaml` copy)
- [ ] `<output>/config/retry-policy.yaml`
- [ ] `<output>/tools/regen.sh`
- [ ] `<output>/tools/oapi-codegen.yaml`
- [ ] `<output>/go.mod`
- [ ] `go test ./...` passed
- [ ] final output excludes `.sdkgen/`

## Regen Command

```bash
./tools/regen.sh
go test ./...
```

## Delivery Notes

- `.sdkgen/` contains intermediate artifacts only and is not part of final SDK deliverable.
