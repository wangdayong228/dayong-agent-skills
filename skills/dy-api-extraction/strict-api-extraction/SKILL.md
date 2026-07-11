---
name: strict-api-extraction
description: Use when official API documentation must be collected exhaustively before OpenAPI or OpenRPC schema work, and completeness matters more than speed. Use when no complete trusted machine-readable spec exists, or the published spec is incomplete, stale, or unverified. Do NOT use when a complete, trusted openapi.json or openrpc.json already exists.
---

# Strict API Extraction

## Core Rule

Collect every official documentation page needed to produce a complete API schema. Until coverage is satisfied, keep discovering and fetching pages from the docs site. Never guess undocumented fields, types, enums, defaults, status codes, or auth requirements.

**Violating the letter of these rules is violating the spirit of these rules.**

## When to Use

- Building or regenerating OpenAPI 3.x / OpenRPC 1.x from official docs
- Verifying that scraped docs are sufficient before schema assembly
- Official docs are fragmented across reference pages, schema pages, auth guides, and error catalogs

## When NOT to Use

- A complete, trusted machine-readable spec already exists — pin and use it directly
- The task is only client codegen from an existing spec — use api-client-generator
- The task is general docs ingestion without schema completeness requirements — use firecrawl-knowledge-ingest

## Scope Boundary

This skill delivers an evidence-complete page corpus (in Firecrawl's default output) plus one human-readable evidence report. Schema assembly (writing openapi.yaml or openrpc.json) is a separate downstream step. State this boundary at task start when the user asks to "reconstruct" or "generate" a spec.

## Storage Convention

**Use Firecrawl defaults. Do not invent a parallel directory tree.**

- Scraped pages land in `.firecrawl/` with Firecrawl's normal filenames (e.g. `.firecrawl/{site}-{path}.md`).
- Do **not** create `.firecrawl/schema-evidence/` or other subfolders unless the user explicitly asks.
- Do **not** rename or move Firecrawl outputs unless the user explicitly asks.
- Ensure `.firecrawl/` is in `.gitignore`. Never commit scraped third-party documentation.
- Human-readable deliverable: **`docs/api-evidence-report.md`** only (see Deliverable).

When citing evidence, use the **actual path under `.firecrawl/`** plus line number: `.firecrawl/docs.example.com-reference-users.md:42`.

## Source Ranking

When sources conflict, prefer higher-ranked evidence:

1. Official machine-readable spec (openapi.json, openrpc.json) from the docs site
2. Main-content documentation tables, parameter lists, response examples (`.firecrawl/*.md`)
3. Cross-page corroboration from auth, error, and support/reference pages

## Loop Contract

Run at most five discovery rounds. Track explicitly:

| Field | Meaning |
| --- | --- |
| `round` | 1 through 5 |
| `frontier` | URLs classified as include/defer, not yet fetched |
| `corpus` | Files under `.firecrawl/` plus URL, title, role metadata recorded in the report |
| `sourced` | Checklist item confirmed with `.firecrawl/...:line` citation |
| `unresolved_ref` | Cross-references without a corpus page yet |
| `unreachable` | URL attempted but blocked (403, 404, login wall, repeated fetch failure) |
| `missing_from_docs` | Exhaustive search completed; official docs silent |

Stop early when every checklist item is `sourced`, `missing_from_docs`, or `unreachable`, and the report records **GO** or **NO-GO**. Stop after round 5 even if gaps remain.

Increment `round` each time step 3 (Discovery) is re-entered. The first pass through step 3 is round 1.

At round 5, reclassify any remaining `unresolved_ref` as `unreachable` (fetch blocked) or `missing_from_docs` (round limit reached).

## Workflow

1. **Identify target schema dialect.**
   - REST → OpenAPI 3.x
   - JSON-RPC → OpenRPC 1.x

2. **Probe machine-readable spec (quick).**
   - Try `/openapi.json`, `/swagger.json`, `/llms.txt` on the docs domain
   - Record outcome in the report Summary (found / incomplete / not found)
   - Complete trusted spec found → stop this skill; pin spec and exit
   - Otherwise continue

3. **Discovery — build the URL frontier.**
   - Start from the official API docs entry URL
   - Use firecrawl-map; outputs stay in `.firecrawl/` per Firecrawl defaults
   - Enumerate sidebar, reference index, version branches, pagination, search, cross-links
   - Classify each URL: `include`, `exclude`, or `defer` (see Page Scope)

4. **Fetch — collect raw pages.**
   - Use firecrawl-scrape with `--only-main-content` for readable markdown into `.firecrawl/`
   - Preserve code blocks, tables, and parameter lists verbatim
   - Follow unresolved cross-references by adding linked URLs to the frontier
   - **Optional escalation:** if a ReadMe/JS-heavy page lacks schema in `.md`, scrape `-f rawHtml` to `.firecrawl/` and search for embedded schema signals — do not make this the default for every page

5. **Coverage check — compare corpus against the checklist.**
   - Every item: `sourced` with `.firecrawl/...:line`, or `missing_from_docs`, or `unreachable`
   - Flag `unresolved_ref` when a referenced section is not yet in the corpus

6. **Close gaps — loop until done or round limit reached.**
   - Gaps or `unresolved_ref` → return to step 3 if `round < 5`
   - Two failed fetch attempts for the same URL → mark `unreachable`
   - **NO-GO** if blocking gaps remain and user has not approved partial scope

7. **Deliver `docs/api-evidence-report.md`.**

## Page Scope

**Include:**
- API reference, endpoints, methods, operations
- Request/response schema pages, object/type definitions
- Authentication, authorization, scopes, API keys
- Error codes, error response formats
- Webhooks, callbacks, subscriptions (if documented)
- Rate limits when they define request/response contract details
- Support/reference pages: enum lists, instruments, symbols, exchanges, or other lookup tables referenced by endpoints

**Exclude (unless they define schema elements):**
- Tutorials, quick starts, getting-started guides
- SDK usage examples without schema definitions
- Changelogs, blog posts, release notes
- Pricing, support, or marketing pages

## Coverage Checklist

Every item must be `sourced`, `missing_from_docs`, or `unreachable`:

| Element | Required evidence |
| --- | --- |
| Endpoint / RPC method | Name, HTTP method or RPC name, `.firecrawl/...:line` |
| Parameters | Name, location, type, required/optional |
| Request body | Content-type, schema or field list |
| Responses | Each documented status; body schema or explicit "no body" |
| Schemas / objects | Field names, types, required fields, enum values |
| Authentication | Scheme type, header/param name, scopes if applicable |
| Errors | Documented error codes or error object shape |
| Webhooks / callbacks | Event types, payload schema (if documented) |
| Cross-references | Referenced pages present in `.firecrawl/` |

## No-Guess Rules

Forbidden without explicit documentation text:

- Inferring types from example values alone
- Inventing enum members not listed in docs
- Assuming required/optional when docs are silent
- Adding status codes not documented
- Copying patterns from similar endpoints
- Using SDK source code or third-party specs as substitutes
- Probing live API responses to infer fields (unless user explicitly approves live probing)

## Deliverable

Write **`docs/api-evidence-report.md`**:

```markdown
# Strict API Extraction: [API Name]

## Summary
- Target: OpenAPI 3.x | OpenRPC 1.x
- Entry URL: [url]
- Machine-readable spec: [found at URL | probed, not found | incomplete]
- Firecrawl corpus: `.firecrawl/` ([n] files)
- Coverage: [sourced n / total n]
- Gate: **GO** | **NO-GO**

## Corpus Index
| File (under .firecrawl/) | URL | Role |
| --- | --- | --- |
| docs.example.com-reference-users.md | https://... | endpoint-ref |

## Coverage Report
| Element | Status | Source | Notes |
| --- | --- | --- | --- |
| GET /users | sourced | .firecrawl/docs.example.com-reference-users.md:117 | |
| User.email type | missing_from_docs | — | exhaustive search completed |

## Unresolved Items
[List missing_from_docs and unreachable items with searched URLs/paths]

## Next Step
Corpus ready for schema assembly only when Gate is **GO**. Do not assemble until user requests it.
```

**GO** = every in-scope checklist item is `sourced` or explicitly out of scope with user approval.  
**NO-GO** = blocking `missing_from_docs` items remain for required schema elements.

## Rationalization Table

| Excuse | Reality |
| --- | --- |
| "The example shows it's a string" | Examples are not schema. Mark missing or find the type page. |
| "Other endpoints use the same pattern" | Pattern matching is guessing. |
| "We have enough to start the spec" | Continue fetching until coverage passes or NO-GO is explicit. |
| "I'll reorganize Firecrawl files into schema-evidence" | Unnecessary complexity. Use `.firecrawl/` as-is. |
| "A live API call confirms the field" | Live probing is guessing unless user approved it. |

## Red Flags — STOP

- Writing openapi.yaml before the report shows **GO**
- Filling schema fields without a `.firecrawl/...:line` citation
- Stopping while sidebar or cross-refs remain unexplored
- Marking coverage complete with open `unresolved_ref`

## Tooling

| Capability | Preferred tools |
| --- | --- |
| URL discovery | firecrawl-map, firecrawl-search |
| Page fetch | firecrawl-scrape (`--only-main-content`) |
| Spec probe | firecrawl-scrape (`/openapi.json`, `/llms.txt`) |
| JS-heavy / auth-gated | firecrawl-interact, browser navigation |
| Corpus search | `rg` over `.firecrawl/` |

Do not substitute memory, training data, or third-party specs for missing pages.
