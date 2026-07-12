# OpenAPI Readiness: CoinGlass fr-ohlc-histroy

## Summary
- Dialect: OpenAPI 3.x
- Material profile: strict-api-extraction
- Material root: skills/dy-api-extraction/strict-api-extraction/test/coinglass-fr-ohlc-history
- Scope: GET /api/futures/funding-rate/history (`fr-ohlc-histroy`) + auth/errors cross-refs
- Strictness: strict
- Extraction gate (if report present): **GO**
- Schema gate: **NO-GO**
- Output: (none — gaps only)

## Material Inventory
| File | Tier | Role | Notes |
| --- | --- | --- | --- |
| source/raw/llms.txt | A | index | doc discovery |
| source/raw/fr-ohlc-histroy.md | A | endpoint-ref | embedded partial OpenAPI |
| source/raw/authentication.md | A | auth | CG-API-KEY header |
| source/raw/responses-error-codes.md | A | errors | global error codes |
| source/raw/instruments.md | A | cross-ref | exchange/symbol reference |
| source/snapshots/fr-ohlc-histroy-zh.md | B | endpoint-ref | Chinese SPA snapshot |
| docs/api-source-report.md | C | index | not evidence |

## Readiness Checklist
| Element | Status | Evidence (Tier A/B path:line) | Notes |
| --- | --- | --- | --- |
| GET /api/futures/funding-rate/history | sourced | source/raw/fr-ohlc-histroy.md:73-77 | operationId fr-ohlc-histroy |
| Base URL / servers | sourced | source/raw/fr-ohlc-histroy.md:53-56 | https://open-api-v4.coinglass.com |
| Query: exchange | sourced | source/raw/fr-ohlc-histroy.md:80-87 | |
| Query: symbol | sourced | source/raw/fr-ohlc-histroy.md:90-97 | |
| Query: interval | sourced | source/raw/fr-ohlc-histroy.md:100-107 | |
| Query: limit | sourced | source/raw/fr-ohlc-histroy.md:110-118 | |
| Query: start_time | sourced | source/raw/fr-ohlc-histroy.md:121-129 | |
| Query: end_time | sourced | source/raw/fr-ohlc-histroy.md:132-140 | |
| Request body (GET) | N/A | — | GET has no body |
| Response 200 formal schema | missing | source/raw/fr-ohlc-histroy.md:153-157 | embedded OpenAPI schema properties empty |
| Response 400 | sourced | source/raw/fr-ohlc-histroy.md:160-171 | example only |
| Authentication CG-API-KEY | sourced | source/raw/fr-ohlc-histroy.md:60-63; source/raw/authentication.md:22-33 | |
| Global error codes | sourced | source/raw/responses-error-codes.md:11-21 | |
| Cross-ref instruments | sourced | source/raw/instruments.md:5-7 | |

## Gaps (blocking schema generation)
| Element | What's missing | Suggested action |
| --- | --- | --- |
| Response 200 formal JSON Schema | `schema.properties` empty in official embedded OpenAPI; types only in example block | official docs silent — cannot assemble strict schema; user may approve reduced scope |

## User Decision Required
Schema gate **NO-GO** — blocking gap: Response 200 formal schema is missing.

Reply with one option number:

1. **Re-fetch** — run `strict-api-extraction` for additional official pages.
2. **Example fallback** — generate schema from documented Tier A/B examples and mark inferred fields with `x-inferred-from: example`.
3. **Reduced scope** — exclude missing elements from the spec (`out_of_scope`) and generate only the sourced contract.
4. **Stop** — keep `docs/openapi-readiness-report.md` only; do not write `schema/openapi.yaml`.

## Conflicts
| Item | Sources | Resolution |
| --- | --- | --- |
| limit default value | Tier A markdown (1000) vs Tier B SPA (10) | Tier A wins; document in spec notes if GO after scope change |

## Next Step
Schema **NO-GO** — do not write `schema/openapi.yaml` in strict mode. Re-run `strict-api-extraction` if new official schema pages appear, or user approves reduced scope marking response types `out_of_scope`.
