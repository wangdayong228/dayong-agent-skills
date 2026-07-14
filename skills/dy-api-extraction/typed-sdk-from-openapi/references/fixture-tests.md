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
- Detect derived operation key collisions; collision is NO-GO
- If any operation is `retryable` or `idempotent_key_required`, confirm `rate-limit-handler` capability before Phase B
- After policy gate passes, confirm `<output>/config/retry-policy.yaml` is written before Phase A

## Output Verification (GO)

- No deliverable `schema/openapi.yaml` copy is required; `input_spec_path` must be an in-project file (prefer `pipeline/openapi/openapi.yaml`) recorded in the manifest
- `<output>/internal/generated/client.gen.go` exists
- `<output>/internal/transport/` exists
- `<output>/pkg/client/` exists
- `<output>/config/spec-manifest.yaml` exists and records input SHA256
- `<output>/config/retry-policy.yaml` exists and is confirmed
- `<output>/tools/regen.sh` and `<output>/tools/oapi-codegen.yaml` exist and regenerate from the in-project `input_spec_path`
- `<output>/go.mod` exists
- `go test ./...` passes in `<output>/`
- `.sdkgen/` is not part of final output module

## Output Verification (NO-GO)

**Policy gate or preflight NO-GO** (before Phase A):

- `.sdkgen/sdk-readiness-report.md` exists
- optional `.sdkgen/retry-policy.draft.yaml` exists
- no `<output>/` SDK directories are created

**Final SDK gate NO-GO** (after Phase A/B):

- `.sdkgen/sdk-readiness-report.md` records blocking reasons
- partial `<output>/` files may exist but delivery is not claimed
- do not treat partial output as a completed SDK deliverable

## Recommended Report Sections

Use `references/sdk-readiness-report-template.md` and include:

- input trust result
- operation count and policy review table
- explicit GO/NO-GO verdict
- blocking reasons when NO-GO
