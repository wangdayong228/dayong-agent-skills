# Verification Checklist (No Offline Scripts)

This skill intentionally does not ship `test/` or `scripts/` helpers. Verification is runtime checklist driven.

## Preflight Verification

- Confirm input spec is OpenAPI 3.x and pinned
- Record SHA256 in `.sdkgen/sdk-readiness-report.md`
- Confirm `api-client-generator` capability exists before code generation
- Create `.sdkgen/retry-policy.draft.yaml`

## Gate Verification

- Collect user confirmation (`approve all` or explicit overrides)
- Ensure no `policy: unreviewed`
- Ensure all operations are `confirmed: true` before GO

## Output Verification (GO)

- `<output>/schema/openapi.yaml` exists
- `<output>/generated/client.gen.go` exists
- `<output>/internal/transport/` exists
- `<output>/pkg/client/` exists
- `<output>/sdk/spec-manifest.yaml` exists and records input SHA256
- `<output>/sdk/retry-policy.yaml` exists and is confirmed
- `<output>/scripts/regen.sh` exists
- `<output>/go.mod` exists
- `go test ./...` passes in `<output>/`
- `.sdkgen/` is not part of final output module

## Output Verification (NO-GO)

- `.sdkgen/sdk-readiness-report.md` exists
- optional `.sdkgen/retry-policy.draft.yaml` exists
- no SDK code output directories are created

## Recommended Report Sections

Use `references/sdk-readiness-report-template.md` and include:

- input trust result
- operation count and policy review table
- explicit GO/NO-GO verdict
- blocking reasons when NO-GO
