# Pipeline Layout Skills Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `dy-api-extraction` three skills to the approved breaking `pipeline/` layout so stage 1–2 outputs are not top-level, and stage 3 delivers a consumer-clean Go SDK tree.

**Architecture:** Path-only migration per `docs/superpowers/specs/2026-07-14-pipeline-layout-skills-design.md`. No new orchestrator skill. No `coinglass-sdk` migration. Semantics (gates, tiers, retry) unchanged.

**Tech Stack:** Markdown skill docs under `skills/dy-api-extraction/`; repo `README.md`.

## Global Constraints

- Breaking: no dual layout / old-path aliases
- Scope: `dayong-agent-skills` only
- Spec copy removed from typed-sdk deliverable; prefer `pipeline/openapi/openapi.yaml` + manifest SHA256
- `generated/` → `internal/generated/`; `sdk/` → `config/`; regen under `tools/`

## File Map

| File | Change |
| --- | --- |
| `skills/dy-api-extraction/strict-api-extraction/SKILL.md` | New extract paths + gitignore |
| `skills/dy-api-extraction/strict-api-extraction/references/report-template.md` | Examples + downstream pointer |
| `skills/dy-api-extraction/strict-api-extraction/agents/openai.yaml` | Prompt text |
| `skills/dy-api-extraction/openapi-from-sources/SKILL.md` | Profile A + deliverables |
| `skills/dy-api-extraction/openapi-from-sources/references/*` | Templates/evidence/fixture docs |
| `skills/dy-api-extraction/openapi-from-sources/agents/openai.yaml` | Prompt text |
| `skills/dy-api-extraction/typed-sdk-from-openapi/SKILL.md` | Input/output/workflow |
| `skills/dy-api-extraction/typed-sdk-from-openapi/references/*` | All path references |
| `README.md` | Skill blurbs + BREAKING CHANGE |

---

## Task 1: strict-api-extraction

**Files:** SKILL.md, references/report-template.md, agents/openai.yaml

- [x] Replace `source/raw/` → `pipeline/extract/raw/`
- [x] Replace `source/snapshots/` → `pipeline/extract/snapshots/`
- [x] Replace `docs/api-source-report.md` → `pipeline/extract/report.md`
- [x] Gitignore guidance: `.local/`, `.firecrawl/`, `pipeline/extract/raw/`
- [x] Downstream mention: `pipeline/openapi/openapi.yaml`
- [x] Grep skill dir: no old defaults remain as outputs

## Task 2: openapi-from-sources

**Files:** SKILL.md, references/{readiness-report-template,evidence-extensions,fixture-tests}.md, agents/openai.yaml

- [x] Profile A input = `pipeline/extract/{raw,snapshots,report.md}` + `.firecrawl/`
- [x] Deliverables = `pipeline/openapi/openapi.yaml`, `readiness-report.md`, optional `evidence-map.yaml`
- [x] Update all STOP/Workflow/NO-GO/validation text
- [x] Evidence examples use `pipeline/extract/...`
- [x] Grep skill dir for old defaults

## Task 3: typed-sdk-from-openapi

**Files:** SKILL.md, references/{refined-client-patterns,transport-patterns,fixture-tests,sdk-readiness-report-template}.md

- [x] Preferred input `pipeline/openapi/openapi.yaml`; still allow explicit pin
- [x] Output: `internal/generated/`, `config/`, `tools/`; drop deliverable `schema/openapi.yaml` copy
- [x] Workflow / gate / validation checklists updated
- [x] Policy path `config/retry-policy.yaml`
- [x] Grep skill dir for old defaults (`generated/` at output root, `sdk/`, `scripts/regen`)

## Task 4: README + global verify

- [x] Update skill table descriptions to new paths
- [x] Add short BREAKING CHANGE note for layout
- [x] Repo-wide grep under `skills/dy-api-extraction/` for: `source/raw`, `source/snapshots`, `docs/api-source-report`, `docs/openapi-readiness-report`, root `schema/openapi.yaml` as default output, root `generated/` as default deliverable
- [x] Confirm stage chain paths consistent (extract → openapi → internal/generated + config + tools)

## Verification

```bash
rg -n 'source/raw|source/snapshots|docs/api-source-report|docs/openapi-readiness-report' skills/dy-api-extraction/
rg -n 'schema/openapi\.yaml' skills/dy-api-extraction/
rg -n '`sdk/`|scripts/regen|generated/client' skills/dy-api-extraction/typed-sdk-from-openapi/
```

Expect: old paths only if clearly about migration history (should be **zero** in skill bodies after this change). New paths present and consistent.

## Out of scope

- Do not modify `coinglass-sdk`
- Do not add a pipeline orchestrator skill
- Do not commit unless user asks (implementation may leave working tree dirty)
