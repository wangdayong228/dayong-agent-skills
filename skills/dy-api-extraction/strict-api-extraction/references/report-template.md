# Strict API Extraction: [API Name]

## Summary
- Target: OpenAPI 3.x | OpenRPC 1.x
- Entry URL: [url]
- Tier A raw: `source/raw/` ([n] files)
- Tier B snapshots: `source/snapshots/` ([n] files)
- Tier B auxiliary: `.firecrawl/` ([n] files, or none)
- Coverage: [sourced n / total n]
- Gate: **GO** | **NO-GO**

## Source Index
| File | Tier | page_type | source_url | capture_method | Role |
| --- | --- | --- | --- | --- | --- |
| source/snapshots/users.md | B | spa | https://... | ego-browser-snapshotText | endpoint-ref |
| source/raw/openapi.json | A | machine-spec | https://.../openapi.json | serverFetch | machine-spec |
| .firecrawl/docs.example.com-....md | B | static-html | https://... | firecrawl-scrape | auth |

## Coverage Report
| Element | Status | Source (Tier A/B path:line) | Notes |
| --- | --- | --- | --- |
| GET /users | sourced | source/snapshots/users.md:117 | |
| User.email type | missing_from_docs | — | exhaustive search completed |

## Unresolved Items
[List missing_from_docs and unreachable items with searched URLs/paths]

## Next Step
Sources ready for schema assembly only when Gate is **GO**. Do not assemble until user requests it.
