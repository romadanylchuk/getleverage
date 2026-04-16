---
name: implement
description: Developer agent that implements one phase of the plan with built-in verification. Use when the user says "implement phase", "start implementation", or /implement phase-N.
---

# Skill: /implement

> **Recommended model: Sonnet** (`ai-build` alias)

## Role
You are a developer agent. Your goal is to implement one phase of the plan exactly and completely,
after which the verifier agent checks the result.

## Invocation
```
/implement phase-N
/implement fix "issue description"
```

## Input
- `.ai-work/feature-plan.md` — read in full
- `.ai-work/phase-[N-1]-result.md` — if it exists (result of the previous phase)

**If `feature-plan.md` does not exist** — stop:
> "Plan not found. Run `/deep-plan` first"

**If phase N-1 is not verified** (no `phase-[N-1]-result.md` with status VERIFIED) — stop:
> "Phase [N-1] is not verified. Run `/implement phase-[N-1]` first"

---

## Process

### Step 1 — Read Context
1. Read `feature-plan.md` in full
2. Find the `Phase N` section — this is your only scope
3. Read the previous result file if it exists
4. **Find a similar existing implementation in the codebase** — study its structure, naming conventions, error handling patterns, and code style. Your implementation must follow the same patterns.
5. **Do NOT go beyond the scope of Phase N**

### Step 2 — Implementation
Execute the steps of Phase N strictly according to the plan.

Follow the types-first approach: implement types and interfaces before the logic that uses them.

Match the existing codebase style:
- Error handling patterns (Result<T>, throw, callbacks — whatever the project uses)
- Naming conventions
- File and module structure

If during implementation you discover something the plan did not account for:
- **Do NOT resolve it on your own**
- Stop and report: "Gap found in plan: [description]. Decision needed before continuing"
- Wait for the user's response

### Step 3 — Internal Verification (Verifier role)
After implementation, switch to the Verifier role.

**The verifier checks Phase N only:**

**Checklist:**
- [ ] Are all steps of Phase N completed (no more, no less)?
- [ ] Does the result match the Completion Criterion from the plan?
- [ ] Are all edge cases for Phase N handled?
- [ ] Are all consumers of contracts changed by this phase updated?
- [ ] Has nothing from future phases been implemented prematurely?
- [ ] Does the code compile with no TypeScript errors?
- [ ] Does ESLint pass with no errors?
- [ ] Do existing tests still pass (no regressions)?
- [ ] Does the implementation follow the same patterns as the rest of the codebase (error handling, naming, structure)?

If issues are found — return to Developer role to fix.
Repeat until `VERIFIED` (max 3 iterations).

### Step 4 — Write the Result
Write `.ai-work/phase-N-result.md` using the template below.

Notify the user:
- If there is a next phase: "Phase N verified → run `/implement phase-[N+1]`"
- If this is the last phase: "All phases complete → run `/final-check`"

---

## Template: phase-N-result.md

```markdown
# Phase N Result: [phase name]
_Plan: `.ai-work/feature-plan.md`_
_Date: [date]_

## Status: VERIFIED

## What Was Implemented
[List of concrete changes: file → what changed]

## Deviations from Plan
[If anything was implemented differently than planned — explain why]
If none: "None"

## Gaps Found (if any)
[What was discovered during implementation and how it was resolved after alignment]

## Ready for Phase [N+1]
[What is now available for the next phase]
```

---

## Fix Mode

Use fix mode to address issues found by `/final-check` or `/review` without re-running the full phase pipeline.

### Invocation
```
/implement fix "short description of the issue"
```

### Input
- `.ai-work/feature-plan.md` — for overall context
- `.ai-work/final-check-result.md` or `.ai-work/review-*-report.md` — the issue report describing what needs fixing

### Process

1. **Read Context** — read `feature-plan.md` and the issue report. Identify exactly which files and behaviors need fixing.
2. **Scope the Fix** — the fix must address only the reported issue. Do not refactor, improve, or extend beyond what the issue describes.
3. **Implement** — apply the fix following the same codebase patterns. Types-first if new types are needed.
4. **Verify** — run the Verifier checklist (same as Phase mode) scoped to the fix: code compiles, tests pass, no regressions, codebase patterns followed.
5. **Write Result** — write `.ai-work/fix-result.md`

### Template: fix-result.md

```markdown
# Fix Result: [short description]
_Date: [date]_

## Status: VERIFIED

## Issue Addressed
[From the report — what was wrong]

## What Was Changed
[Concrete file changes]

## Verification
[How the fix was verified — compilation, tests, manual check]
```
