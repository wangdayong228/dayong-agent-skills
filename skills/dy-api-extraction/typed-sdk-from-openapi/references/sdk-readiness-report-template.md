# SDK Readiness Report

## Run Metadata

- material_root:
- spec_path: schema/openapi.yaml
- spec_sha256:
- openapi_version:
- operation_count:
- oapi_codegen_version:
- upstream_schema_gate:

## Preflight Checklist

| Check | Status | Notes |
| --- | --- | --- |
| schema/openapi.yaml exists | | |
| operationId unique (or derived) | | |
| servers.url present | | |
| security scheme documented | | |

## Retry Policy Review

- draft_path: sdk/retry-policy.draft.yaml
- confirmed_path: sdk/retry-policy.yaml
- user_approval:
- overrides:

## SDK Gate

**Verdict:** GO | NO-GO

## Deliverables

- [ ] generated/
- [ ] internal/transport/
- [ ] pkg/client/
- [ ] sdk/retry-policy.yaml
- [ ] scripts/regen.sh

## Regen

```bash
./scripts/regen.sh
go test ./...
```
