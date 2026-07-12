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
| A raw | `source/raw/` | HTTP bytes from docs domain (openapi.json, openrpc.json, llms.txt) | Yes | 1 |
| B snapshots | `source/snapshots/` | ego-browser page captures (snapshotText) | Yes | 2 |
| B snapshots | `.firecrawl/` | Firecrawl fallback captures (keep default filenames) | Yes | 3 |
| C derived | `docs/api-source-report.md` | Agent-written index | No | — |

No `schema-evidence` or `corpus` folders. Add `.local/`, `.firecrawl/`, `source/raw/`, and `source/snapshots/` to the **target project** `.gitignore`. Never commit scraped third-party documentation into user projects. (Maintainer test fixtures in skill repos are optional and follow that repo's `.gitignore`.)

Schema fields must trace to Tier A or B with `path:line` (`source/raw/`, `source/snapshots/`, or `.firecrawl/`). The report is never sole evidence.

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

## Prerequisites

Install these skills separately — they are not bundled in this repo:

| Skill | Required | Role |
| --- | --- | --- |
| `ego-browser` | **Yes** | Primary fetch (`serverFetch`, `snapshotText`) |
| `firecrawl-scrape` | No | Tier B fallback for static/spa/interactive pages |
| `firecrawl-map` | No | Bulk URL discovery |

If `ego-browser` is unavailable, write a **NO-GO** report stating the blocker — do not substitute WebFetch or Cursor browser MCP.

## Capture by Page Type

**REQUIRED:** Load `ego-browser` before discovery or fetch. Load `firecrawl-scrape` / `firecrawl-map` only as needed.

Classify each URL, pick first-try tool, record `page_type`. Two failed attempts → fallback or `unreachable`.

| `page_type` | First try | Tier | Fallback |
| --- | --- | --- | --- |
| `machine-spec` | `serverFetch` (`.json`, `.yaml`, `.md`, `llms.txt`) | A → `source/raw/` | `browserFetch`; store only if valid JSON/YAML/text — otherwise mark URL `unreachable` and note in report |
| `static-html` | `serverFetch` or `snapshotText` | B → `source/snapshots/` | firecrawl-scrape → `.firecrawl/` |
| `spa` | `openOrReuseTab` + wait + `snapshotText` | B → `source/snapshots/` | firecrawl-scrape → `.firecrawl/` |
| `interactive` | expand tabs/accordions/pagination, then `snapshotText` | B → `source/snapshots/` | firecrawl-scrape → `.firecrawl/` |
| `auth-gated` | ego-browser with user session | B | `unreachable` (login required) |

Firecrawl is auxiliary only — bulk URL map (`firecrawl-map`) and Tier B fallback, never the sole fetch path.

## Loop Contract

At most **5 discovery rounds**. Track: `round`, `frontier`, `sourced`, `unresolved_ref`, `unreachable`, `missing_from_docs`, `round_limit_deferred`.

Stop when every checklist item has a terminal status (`sourced`, `missing_from_docs`, `unreachable`, `N/A`, or `out_of_scope`), no pending cross-ref `unresolved_ref` remains, and Gate is **GO** or **NO-GO**. Increment `round` each re-entry to Discovery. At round 5: reclassify remaining **pending cross-ref** `unresolved_ref` (URLs not yet fetched) — fetch blocked → `unreachable`; not attempted due to round limit → `round_limit_deferred` (list URL in Unresolved Items; **not** `missing_from_docs`). Defer unvisited in-scope frontier URLs the same way. `unreachable` is not `missing_from_docs` — never guess content for unreachable URLs. **`missing_from_docs` means exhaustive search completed and official docs are silent** — never use it for URLs simply not yet fetched. **Evidence conflicts** (Tier A vs B disagree) are not pending cross-refs — record with conflict rank in Unresolved Items.

## Workflow

1. **Dialect & scope** — REST → OpenAPI 3.x; JSON-RPC → OpenRPC 1.x. Record in-scope endpoints/APIs in report Summary `Scope` (from user request; if unclear, ask before discovery).
2. **Probe Tier A** — per dialect, `serverFetch` → `source/raw/`:
   - OpenAPI: `/openapi.json`, `/swagger.json`, `/llms.txt`
   - OpenRPC: `/openrpc.json`, `/llms.txt`
   **Pin and short-circuit discovery** (skip steps 3–6 page fetch loop) only when a **complete, trusted** spec is confirmed (see below). **Always** run step 5 Coverage against the pinned spec, then step 7. If step 5 finds in-scope checklist gaps that require documentation **outside** the pinned spec, **resume discovery** (steps 3–6; round counter continues, does not reset) — do not mark `missing_from_docs` without exhaustive search. Gate **GO** only per Deliverable below.
3. **Discovery** — ego-browser entry URL; walk sidebar, index, version switcher, cross-links; classify URLs (Page Scope); optional `firecrawl-map`
4. **Fetch** — per Capture by Page Type → `source/raw/` or `source/snapshots/` (ego-browser); Firecrawl fallback → `.firecrawl/` (still Tier B). Expand hidden content; chase cross-refs into frontier
5. **Coverage** — each checklist item: `sourced` (`path:line`), `missing_from_docs`, `unreachable`, `N/A` (not applicable, e.g. GET has no body), or `out_of_scope` (user-approved reduced scope); flag pending cross-ref URLs as `unresolved_ref`
6. **Loop** — items lacking a terminal status (`sourced`, `missing_from_docs`, `unreachable`, `N/A`, `out_of_scope`), pending cross-ref `unresolved_ref`, or frontier URLs → step 3 if `round < 5`; at `round >= 5`, reclassify per Loop Contract then proceed to step 7; two fetch failures → `unreachable`; any `round_limit_deferred` → **NO-GO** unless user explicitly approves reduced scope (update Summary `Scope`, mark affected checklist items `out_of_scope`, keep deferred URLs in Unresolved Items)
7. **Report** — write `docs/api-source-report.md` per `references/report-template.md`

**Complete, trusted spec (step 2 short-circuit criteria):** all must pass before skipping discovery — (1) parses as valid OpenAPI 3.x or OpenRPC 1.x; (2) covers the in-scope endpoints/operations or RPC methods (cross-check `llms.txt` or docs index when available); (3) not obviously partial (empty `paths`/`methods`, single operation when docs list many, version mismatch); (4) user has not flagged it stale/unverified. Any doubt → treat as incomplete and continue discovery. Short-circuit still requires step 7 report — never finish without `docs/api-source-report.md`.

## Page Scope

**Include:** endpoints, schemas/types, auth, errors, webhooks, rate limits affecting contract, enum/symbol reference pages.

**Exclude:** tutorials, SDK-only examples, changelogs, marketing — unless they define schema elements. Overview/index pages: use for discovery only; chase cross-refs into frontier rather than treating as final evidence.

## Coverage Checklist

Every item: `sourced`, `missing_from_docs`, `unreachable`, `N/A`, or `out_of_scope`.

| Element | Required evidence |
| --- | --- |
| Endpoint / RPC | Name, method, Tier A/B `path:line` |
| Parameters | Name, location, type, required/optional |
| Request body | Content-type, schema or field list |
| Responses | Each status; body schema or "no body" |
| Schemas / objects | Fields, types, required, enums |
| Authentication | Scheme, header/param, scopes |
| Errors | Codes or error object shape |
| Rate limits | Contract-affecting limits when documented |
| Webhooks | Event types, payload schema |
| Cross-references | Referenced pages in snapshots or raw |

## No-Guess & Red Flags

Forbidden without Tier A/B text: infer types from examples; invent enums; assume required/optional; add status codes; copy similar endpoints; use SDK or third-party specs; probe **live API product** (docs-domain raw endpoints OK).

| Excuse → Reality |
| --- |
| "Firecrawl is faster" → ego-browser primary; Firecrawl fallback only |
| "Report says sourced" → Tier C is not evidence; need Tier A/B `path:line` (`source/raw/`, `source/snapshots/`, or `.firecrawl/`) |
| "Example shows string" → examples ≠ schema |
| "Live API confirms field" → guessing unless user approved |

**STOP:** citing report alone; Firecrawl-only when ego-browser available; writing openapi.yaml before **GO**; stopping with unexplored sidebar/cross-refs; open `unresolved_ref` marked complete; finishing without `docs/api-source-report.md`.

Do not substitute memory, training data, or third-party specs for missing sources.

## Deliverable

Write **`docs/api-source-report.md`** (Tier C) using `references/report-template.md`.

**GO** = every in-scope item has a terminal collection status — `sourced` from Tier A/B, `N/A`, user-approved `out_of_scope`, or `missing_from_docs` after exhaustive search; no pending cross-ref `unresolved_ref`; no `round_limit_deferred` unless user approved reduced scope (Scope updated, deferred items `out_of_scope`). **Evidence conflicts** (Tier A vs B disagree): cite the **winning tier** (rank 1 > 2 > 3) in Coverage Report `path:line`, and record the conflict in Unresolved Items with both ranks — conflicts do not block extraction **GO**.  
**NO-GO** = any in-scope item lacks a terminal status; any required in-scope element is `unreachable`; or any `round_limit_deferred` without user-approved reduced scope.

`missing_from_docs` completes extraction but does **not** imply schema readiness — downstream `openapi-from-sources` strict mode treats those items as blocking unless the user approves reduced scope or example-fallback.
