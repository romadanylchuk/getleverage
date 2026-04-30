---
name: implement
description: Developer agent that implements one phase of the plan with built-in verification. Use when the user says "implement phase", "start implementation", or /workflow:implement phase-N.
---

# Skill: /workflow:implement

> **Recommended model: Sonnet**

## Role
You are a developer agent. Your goal is to implement one phase of the plan exactly and completely,
after which the verifier role checks the result.

## Modes

**Manual mode** (default): no `.ai-work/orchestrator-context.json` present. Behave as today, print user-facing notifications.

**Autonomous mode**: `.ai-work/orchestrator-context.json` exists. Read inputs from `.ai-work/briefs/<current_brief>/`, write outputs there, exit silently after writing.

## Invocation
```
/workflow:implement phase-N
/workflow:implement fix "issue description"
```

## Input

> **Path notation:** `.ai-work/[briefs/<current_brief>/]<file>` is shorthand for two paths. Manual mode resolves to `.ai-work/<file>`. Autonomous mode resolves to `.ai-work/briefs/<current_brief>/<file>`.

- `.ai-work/[briefs/<current_brief>/]feature-plan.md` — read in full
- `.ai-work/[briefs/<current_brief>/]phase-[N-1]-result.md` — if it exists
- `.ai-work/profile.json` — drives all language/tooling decisions
- `.ai-work/code-map.json` — used for navigation only, not as content source

**If `feature-plan.md` does not exist** — stop:
> "Plan not found. Run `/workflow:deep-plan` first"

**If phase N-1 is not verified** (no `phase-[N-1]-result.md` with status VERIFIED) — stop:
> "Phase [N-1] is not verified. Run `/workflow:implement phase-[N-1]` first"

**If `profile.json` does not exist** — stop and tell the user to run `/orchestrator:bootstrap` first (or accept conservative defaults if they confirm).

---

## Process

### Step 1 — Read Context
1. Read `feature-plan.md` in full
2. Find the `Phase N` section — this is your only scope
3. Read the previous result file if it exists
4. Read `profile.json` — note `build.command`, `lint.command` (if present), `test.command` (if present), `patterns`, `type_system`
5. **Code map navigation** — if `code-map.json` exists, scan for files matching the patterns and similar implementations. Use it to narrow your search.
6. **Read actual files** for every file you will modify, every file whose contract you depend on, and 1-2 similar existing implementations to match style. The code-map is navigation; reading actual source is mandatory for content.
7. **Do NOT go beyond the scope of Phase N**

### Step 2 — Implementation
Execute the steps of Phase N strictly according to the plan.

If `profile.contracts_first` is true, implement contracts (types, signatures, schemas) before the logic that uses them.

Match the existing codebase style according to `profile.patterns`:
- Error handling pattern from `profile.patterns.error_handling`
- Naming conventions from `profile.patterns.naming`
- File and module structure (observe and match)

If during implementation you discover something the plan did not account for:
- **Do NOT resolve it on your own**
- Manual mode: stop and report "Gap found in plan: [description]. Decision needed before continuing"
- Autonomous mode: write the gap to `phase-N-result.md` under `## Gaps Found`, set status to `GAP`, and exit. The orchestrator escalates.

### Step 3 — Internal Verification (Verifier role)
After implementation, switch to the Verifier role.

**The verifier checks Phase N only.**

**Checklist:**
- [ ] Are all steps of Phase N completed (no more, no less)?
- [ ] Does the result match the Completion Criterion from the plan?
- [ ] Are all edge cases for Phase N handled?
- [ ] Are all consumers of contracts changed by this phase updated?
- [ ] Has nothing from future phases been implemented prematurely?
- [ ] Does `profile.build.command` succeed with no errors?
- [ ] If `profile.lint` is non-null: does `profile.lint.command` succeed with no errors?
- [ ] If `profile.test` is non-null: does `profile.test.command` pass (no regressions)?
- [ ] Does the implementation follow `profile.patterns` (error handling, naming, structure)?
- [ ] **Actual-file reads cited**: for every file modified or whose contract was depended on, did the implementation cite reading the actual source file (not only the code-map entry)?

**Conditional checks** — skip silently if the corresponding `profile` field is null:
- Lint check skipped when `profile.lint == null`.
- Test check skipped when `profile.test == null`.
- Type-system specific checks skipped when `profile.type_system == "none"`.

If issues are found — return to Developer role to fix.
Repeat until `VERIFIED` (max 3 iterations).

### Step 4 — Write the Result
Write `phase-N-result.md` using the template below.

**Manual mode notify:**
- If there is a next phase: "Phase N verified → run `/workflow:implement phase-[N+1]`"
- If this is the last phase: "All phases complete → run `/workflow:final-check`"

**Autonomous mode:** exit silently after writing.

---

## Template: phase-N-result.md

```markdown
# Phase N Result: [phase name]
_Plan: `feature-plan.md`_
_Date: [date]_

## Status: VERIFIED

## What Was Implemented
[List of concrete changes: file → what changed]

## Files Read
[Files actually read for contract/style decisions — required for verifier check]

## Verification
- Build: PASS (`profile.build.command`)
- Lint: PASS / SKIPPED (per profile)
- Tests: PASS / SKIPPED (per profile)
- Patterns: matched

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

Use fix mode to address issues found by `/workflow:final-check` or `/workflow:review` without re-running the full phase pipeline.

### Invocation
```
/workflow:implement fix "short description of the issue"
```

### Input
- `feature-plan.md` — for overall context
- `final-check-result.md` or `review-N-report.md` or `fix-N-result.md` (whichever issue report applies)
- `profile.json`
- `code-map.json`

### Process

1. **Read Context** — read `feature-plan.md`, the issue report, and `profile.json`. Identify exactly which files and behaviors need fixing. Read the actual source files.
2. **Scope the Fix** — address only the reported issue. Do not refactor, improve, or extend beyond what the issue describes.
3. **Implement** — apply the fix following `profile.patterns`. Contracts-first if new contracts are needed and `profile.contracts_first` is true.
4. **Verify** — run the Verifier checklist scoped to the fix: `profile.build.command`, lint/test if non-null, no regressions, patterns matched, actual-file reads cited.
5. **Write Result** — write `fix-<id>-result.md` (e.g., `fix-1-result.md` for the first fix in this brief, or `fix-FN-result.md` for a final-check-driven fix).

### Template: fix-result.md

```markdown
# Fix Result: [short description]
_Date: [date]_

## Status: VERIFIED

## Issue Addressed
[From the report — what was wrong]

## What Was Changed
[Concrete file changes]

## Files Read
[Files actually read]

## Verification
- Build: PASS
- Lint: PASS / SKIPPED
- Tests: PASS / SKIPPED
- No regressions confirmed
```
