---
name: strict-api-extraction
description: Use when official API documentation must be collected exhaustively before OpenAPI or OpenRPC schema work, and completeness matters more than speed. Use when no complete trusted machine-readable spec exists, or the published spec is incomplete, stale, or unverified. Do NOT use when a complete, trusted openapi.json or openrpc.json already exists.
---

# Strict API Extraction

## Core Rule

Collect every official documentation page needed to produce a complete API schema. Until coverage is satisfied, keep discovering and fetching pages from the docs site. Never guess undocumented fields, types, enums, defaults, status codes, or auth requirements.

**Violating the letter of these rules is violating the spirit of these rules.**

## When to Use / NOT

**Use:** building OpenAPI 3.x / OpenRPC 1.x from official docs; fragmented or JS-heavy doc portals (ReadMe, Stoplight, etc.).

**NOT:** complete trusted spec already exists (pin it); client codegen only → `api-client-generator`; general docs ingest without schema completeness → `firecrawl-knowledge-ingest`.

## Scope Boundary

Deliver **source artifacts** (Tier A/B) plus one **derived** report (Tier C). Schema assembly is downstream — state this when the user asks to "reconstruct" or "generate" a spec.

## Tiers, Storage, Evidence

| Tier | Location | What | Cite as evidence? | Conflict rank |
| --- | --- | --- | --- | --- |
| A raw | `source/raw/` | HTTP bytes from docs domain (openapi.json, llms.txt) | Yes | 1 |
| B snapshots | `source/snapshots/` | Page captures (snapshotText, Firecrawl) | Yes | 2 (ego-browser) / 3 (Firecrawl) |
| C derived | `docs/api-source-report.md` | Agent-written index | No | — |

Also: `.firecrawl/` for Firecrawl auxiliary output — do not rename. No `schema-evidence` or `corpus` folders. Add `.local/` and `.firecrawl/` to `.gitignore`.

Schema fields must trace to Tier A or B with `path:line`. The report is never sole evidence.

**Snapshot frontmatter** (Tier A raw records `page_type` in report Source Index only):

```yaml
---
source_url: https://docs.example.com/reference/users
page_type: spa
capture_method: ego-browser-snapshotText
fetched_at: 2026-07-11T12:00:00Z
tier: B
---
```

## Capture by Page Type

**REQUIRED:** Load `ego-browser` before discovery or fetch. Do not substitute WebFetch or Cursor browser MCP. Load `firecrawl-scrape` / `firecrawl-map` only as needed.

Classify each URL, pick first-try tool, record `page_type`. Two failed attempts → fallback or `unreachable`.

| `page_type` | First try | Tier | Fallback |
| --- | --- | --- | --- |
| `machine-spec` | `serverFetch` (`.json`, `.yaml`, `.md`, `llms.txt`) | A → `source/raw/` | `browserFetch` |
| `static-html` | `serverFetch` or `snapshotText` | B | firecrawl-scrape |
| `spa` | `openOrReuseTab` + wait + `snapshotText` | B | firecrawl-scrape |
| `interactive` | expand tabs/accordions/pagination, then `snapshotText` | B | firecrawl-scrape |
| `auth-gated` | ego-browser with user session | B | `unreachable` (login required) |

Firecrawl is auxiliary only — bulk URL map (`firecrawl-map`) and Tier B fallback, never the sole fetch path.

## Loop Contract

At most **5 discovery rounds**. Track: `round`, `frontier`, `sources`, `sourced`, `unresolved_ref`, `unreachable`, `missing_from_docs`.

Stop when every checklist item is `sourced`, `missing_from_docs`, or `unreachable` and Gate is **GO** or **NO-GO**. Increment `round` each re-entry to Discovery. At round 5, reclassify remaining `unresolved_ref`.

## Workflow

1. **Dialect** — REST → OpenAPI 3.x; JSON-RPC → OpenRPC 1.x
2. **Probe Tier A** — `serverFetch` `/openapi.json`, `/swagger.json`, `/llms.txt` → `source/raw/`; complete spec found → pin and exit
3. **Discovery** — ego-browser entry URL; walk sidebar, index, version switcher, cross-links; classify URLs (Page Scope); optional `firecrawl-map`
4. **Fetch** — per Capture by Page Type → `source/raw/` or `source/snapshots/`; expand hidden content; chase cross-refs into frontier
5. **Coverage** — each checklist item: `sourced` (`path:line`), `missing_from_docs`, or `unreachable`; flag `unresolved_ref`
6. **Loop** — gaps → step 3 if `round < 5`; two fetch failures → `unreachable`; blocking gaps → **NO-GO** unless user approves partial scope
7. **Report** — write `docs/api-source-report.md` per `references/report-template.md`

## Page Scope

**Include:** endpoints, schemas/types, auth, errors, webhooks, rate limits affecting contract, enum/symbol reference pages.

**Exclude:** tutorials, SDK-only examples, changelogs, marketing — unless they define schema elements.

## Coverage Checklist

Every item: `sourced`, `missing_from_docs`, or `unreachable`.

| Element | Required evidence |
| --- | --- |
| Endpoint / RPC | Name, method, Tier A/B `path:line` |
| Parameters | Name, location, type, required/optional |
| Request body | Content-type, schema or field list |
| Responses | Each status; body schema or "no body" |
| Schemas / objects | Fields, types, required, enums |
| Authentication | Scheme, header/param, scopes |
| Errors | Codes or error object shape |
| Webhooks | Event types, payload schema |
| Cross-references | Referenced pages in snapshots or raw |

## No-Guess & Red Flags

Forbidden without Tier A/B text: infer types from examples; invent enums; assume required/optional; add status codes; copy similar endpoints; use SDK or third-party specs; probe **live API product** (docs-domain raw endpoints OK).

| Excuse → Reality |
| --- |
| "Firecrawl is faster" → ego-browser primary; Firecrawl fallback only |
| "Report says sourced" → Tier C is not evidence; need raw/snapshots `path:line` |
| "Example shows string" → examples ≠ schema |
| "Live API confirms field" → guessing unless user approved |

**STOP:** citing report alone; Firecrawl-only when ego-browser available; writing openapi.yaml before **GO**; stopping with unexplored sidebar/cross-refs; open `unresolved_ref` marked complete.

Do not substitute memory, training data, or third-party specs for missing sources.

## Deliverable

Write **`docs/api-source-report.md`** (Tier C) using `references/report-template.md`.

**GO** = every in-scope item `sourced` from Tier A/B or explicitly out of scope with user approval.  
**NO-GO** = blocking `missing_from_docs` for required schema elements.
