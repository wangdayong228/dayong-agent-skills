# OpenAPI Readiness: [API Name]

## Summary
- Dialect: OpenAPI 3.x
- Material profile: strict-api-extraction | ad-hoc
- Material root: [path]
- Scope: [in-scope endpoints/operations]
- Strictness: strict | example-fallback
- Extraction gate (if report present): **GO** | **NO-GO** | n/a
- Schema gate: **GO** | **NO-GO** | **GO (example-fallback)** | **GO (reduced-scope)**
- Output: `pipeline/openapi/openapi.yaml` | (none — gaps only)

## Material Inventory
| File | Tier | Role | Notes |
| --- | --- | --- | --- |
| pipeline/extract/raw/example.md | A | endpoint-ref | embedded OpenAPI fragment |

## Readiness Checklist
| Element | Status | Evidence (Tier A/B path:line) | Notes |
| --- | --- | --- | --- |
| GET /example | sourced | pipeline/extract/raw/example.md:73 | |
| Request body (GET) | N/A | — | GET has no body |
| Response 200 schema | missing | pipeline/extract/raw/example.md:153 | official schema empty |
| Authentication | sourced | pipeline/extract/raw/auth.md:22 | |

## Gaps (blocking schema generation)
| Element | What's missing | Suggested action |
| --- | --- | --- |
| Response 200 schema | formal field types | re-fetch docs or approve reduced scope |

## User Decision Required
Schema gate **NO-GO** — blocking gap: [short reason].

Reply with one option number:

1. **Re-fetch** — run `strict-api-extraction` for additional official pages.
2. **Example fallback** — generate schema from documented Tier A/B examples and mark inferred fields with `x-inferred-from: example`.
3. **Reduced scope** — exclude missing elements from the spec (`out_of_scope`) and generate only the sourced contract.
4. **Stop** — keep `pipeline/openapi/readiness-report.md` only; do not write `pipeline/openapi/openapi.yaml`.

## User Decision Applied
[Only after user chooses option 2 or 3. Record the selected option and approval text.]

## Conflicts
| Item | Sources | Resolution |
| --- | --- | --- |
| [optional] | Tier A vs B | winning tier + detail |

## Next Step
- Schema **NO-GO** → wait for user option number
- Schema **GO (example-fallback)** → review `x-inferred-from: example` fields before client generation
- Schema **GO (reduced-scope)** → review `out_of_scope` exclusions before client generation
- Schema **GO** → run `api-client-generator` (generic) or `typed-sdk-from-openapi` (Go) on `pipeline/openapi/openapi.yaml`
