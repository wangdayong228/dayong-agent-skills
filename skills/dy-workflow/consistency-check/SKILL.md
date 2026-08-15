---
name: consistency-check
description: Use after verification-before-completion and before claiming work is done — cross-checks consistency across artifacts, sections, files, and configuration; catches contradictions that verification alone misses
---

# Consistency Check

## Overview

Verification proves each piece works in isolation.
Consistency proves the pieces agree with each other.

A build can pass and tests can be green while the code contradicts the plan, the config doesn't match the code, and section A says the opposite of section B.

**Core principle:** No contradiction left behind.

## The Iron Law

```
NO COMPLETION CLAIM WITHOUT A COMPLETED CONSISTENCY CHECKLIST
```

If you haven't output the checklist in this message, you haven't checked consistency. Period.

## When To Apply

After `verification-before-completion` passes, BEFORE claiming work is done, committing, or creating a PR.

## The Consistency Gate

```
For each artifact touched in this change:

1. IDENTIFY: What other artifacts should agree with it?
2. READ: Actually read both sides (don't assume — re-read, don't recall)
3. DIFF: Do they say the same thing?
4. CONTRADICTION FOUND?
   → Fix the inconsistency
   → Re-run check
5. ALL CLEAR: Mark as passed in the checklist

Skip any artifact pair = unknown inconsistency risk
```

## Five Dimensions of Consistency

### 1. Conversational Consistency

**Conclusions stated now must not contradict decisions made earlier in the same conversation.**

| Check | Method |
|-------|--------|
| Current conclusion vs earlier decisions | Review all explicitly agreed decisions in the conversation; compare one by one |
| Current conclusion vs earlier rejections | Were any explicitly rejected approaches quietly revived? |
| Current conclusion vs user preferences | Were any user-stated preferences or constraints violated? |

**Red flags:**
- Earlier said "won't do X", now committed code does X
- User said "use approach A", implementation chose B with no justification
- User corrected an error, same error reappears

### 2. Longitudinal Consistency

**Within a single artifact, statements in different places must not contradict each other.**

| Check | Method |
|-------|--------|
| Cross-section conclusion alignment | List all conclusion statements; compare pairwise |
| File beginning vs end logic | Read first and last paragraphs; check for reversal |
| Same symbol used consistently | grep all occurrences of the symbol; compare context |
| Same question answered consistently | Search keywords; collect all relevant passages; cross-compare |

**Red flags:**
- Chapter 3 says "use approach A", chapter 6 quietly uses approach B
- Introduction says "won't do X", appendix contains X implementation
- Same variable means one thing at the top of the file, something else at the bottom

### 3. Lateral Consistency (Cross-Artifact)

**Different artifacts must align with each other.**

| Check | Method |
|-------|--------|
| Implementation vs plan | Read plan → read implementation → compare line by line |
| Code vs PR/commit description | Description says A changed → what files actually changed? |
| Interface signature vs all callers | After signature change, grep all references; confirm every one updated |
| Frontend vs backend contract | Fields frontend expects → fields backend actually returns |
| Type definitions vs runtime data | interface/type definition → actual assignment/passing |

**Red flags:**
- Plan says Redis cache, code uses in-memory cache
- PR title says "fix login bug", diff also changes payment module
- Function signature changed but one call site wasn't updated

### 4. Configuration Consistency

**Environment variables, config files, and code must align.**

| Check | Method |
|-------|--------|
| New env var propagated | grep code for `process.env.X` → check `.env.example` lists it |
| Default values aligned | Default in code vs default in config file |
| Cross-environment coverage | `.env.development` vs `.env.production` — both cover the new variable? |

### 5. Documentation Consistency

**Documentation must match actual code behavior.**

| Check | Method |
|-------|--------|
| API docs vs actual routes | Documented endpoint → actual handler behavior |
| README commands vs actual | Copy-paste and run README commands |
| Comment assumptions vs code logic | Read comment → read corresponding code → compare |

## Mandatory Output: Consistency Checklist

Before claiming completion, **the following checklist must be output**, with each item marked ✅ or ❌ (with gap description):

```
Consistency Checklist:
  Conversational
    □ Current conclusions don't contradict earlier decisions
    □ No previously rejected approaches quietly revived
    □ No user preferences/constraints violated
  Longitudinal
    □ [specific artifact name] sections are internally consistent
    □ Key symbols/terms used consistently throughout
  Lateral
    □ Implementation matches plan
    □ Code changes match PR description
    □ Interface changes propagated to all callers
  Configuration
    □ New config items added to config templates
    □ All environments covered
  Documentation
    □ API docs/README match actual behavior

Verdict: [All clear / Known gaps documented: (list)]
```

No checklist output = no consistency check performed. No exceptions.

## Red Flags — STOP (and Rationalizations They Expose)

| Red flag / Excuse | Reality |
|-------------------|---------|
| "I think section X says..." | You didn't read it. Go read it. |
| "Plan was a draft" | Either update the plan or change the code — no gap allowed. |
| "I'll update docs later" | "Later" never comes. Do it now or drop the claim. |
| "That other section is outdated" | Outdated = inconsistent. Fix it or flag it. |
| "Close enough" | Close ≠ consistent. State the gap explicitly. |
| "Tests pass so it's fine" | Tests check behavior, not consistency. |
| "Probably consistent" / "Should be fine" / "Looks aligned" | Guessing = not checking. |
| Two sections use the same term differently | Ambiguous terminology = latent misunderstanding. |
| A decision silently reversed elsewhere | Silent reversal = team divergence risk. |
| PR description mentions fewer/more files than changed | Misleading description = reviewer distrust. |

## Why This Matters

Verification catches broken code. Consistency catches broken promises:
- Earlier you said X, now you ship Y → trust lost
- Document A says Strategy X, Document B assumes Strategy Y → team split, rework
- Code changed but plan wasn't updated → next person follows a dead path
- Config added to code but not `.env.example` → next dev's app crashes silently
- PR says "minor refactor" but changes 20 files → reviewer distrust, audit overhead

## Relationship to verification-before-completion

`verification-before-completion` answers: "Does it work?"
`consistency-check` answers: "Does it agree with itself and everything around it?"

Both must pass. Run verification first, then consistency. The consistency checklist is the final gate before any completion claim.
