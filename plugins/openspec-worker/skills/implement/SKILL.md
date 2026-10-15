---
name: implement
description: Developer agent for openspec-worker. Implements one task group of an OpenSpec change's tasks.md with built-in verification and ticks completed tasks, or applies one fix from a review/verify report. Spawned by /openspec-worker:run; not for direct use.
---

# Skill: /openspec-worker:implement

> **Recommended model: Sonnet** (Opus for verify-driven fixes)

## Role
Implement exactly one task group (or one fix), verify it, tick its tasks in `tasks.md`, and record the result.

## Invocation
```
/openspec-worker:implement group-N
/openspec-worker:implement fix review-N "<summary>"
/openspec-worker:implement fix verify "<summary>"
```

## Preconditions
`.openspec-worker/run-context.json` → `<id>`. `$OS` = `profile.openspec.command`. `tasks.md` and `runs/<id>/plan-notes.md` must exist. For `group-N` with N > 1, every task of groups 1..N-1 must be checked (`$OS instructions apply --change <id> --json`) — else write `group-N-result.md` with status `GAP` ("previous group incomplete") and exit.

## Input
- `$OS instructions apply --change <id> --json` → `contextFiles`, `tasks[]` with `sourcePath` and `line`
- `openspec/changes/<id>/tasks.md` — your scope is group N only
- `openspec/changes/<id>/specs/**` — the scenarios your tasks implement (behavior contract)
- `openspec/changes/<id>/design.md` (if present) — decisions you must follow
- `.openspec-worker/runs/<id>/plan-notes.md` — files, contracts, completion criterion for group N
- previous `group-*-result.md` files
- `.openspec-worker/profile.json`, `code-map.json` (navigation only)

## Process — group mode

### Step 1 — Context
Read the inputs above. Read the **actual source** of every file you will modify, every file whose contract you depend on, and 1–2 similar implementations for style. Do not go beyond group N.

### Step 2 — Implement
Do group N's tasks in order. Contracts first when `profile.contracts_first`. Follow `profile.patterns` and the design Decisions. Behavior must match the spec scenarios exactly (error messages, boundaries).

If you find something the specs/design/plan did not account for: **do not decide it yourself.** Write the result with status `GAP` and a `## Gaps Found` section, leave the affected tasks unchecked, and exit.

### Step 3 — Verify (verifier role)
- [ ] Every task of group N done — no more, no less; nothing from later groups.
- [ ] Each task's stated verification actually performed and passing.
- [ ] Scenarios covered by this group behave as specified.
- [ ] Consumers of changed contracts updated.
- [ ] `profile.build.command` passes.
- [ ] `profile.lint.command` passes (skip if lint is null).
- [ ] `profile.test.command` passes, no regressions (skip if test is null).
- [ ] Patterns followed.
- [ ] Actual-file reads cited for every modified or depended-on file.
Fix and re-verify, max 3 iterations.

### Step 4 — Tick tasks
For each task of group N that is fully implemented and verified: change `- [ ]` to `- [x]` at its `sourcePath`/`line`. Never tick partial work. Re-run `$OS instructions apply --change <id> --json` and confirm the group's tasks show `done: true`.

### Step 5 — Result
Write `.openspec-worker/runs/<id>/group-N-result.md`:

```markdown
# Group N Result: <group name>
_Change: <id> · Date: YYYY-MM-DD_

## Status: VERIFIED | GAP

## Tasks
- [x] N.1 ... — <evidence: test name / command output>
- [ ] N.3 ... — not done (GAP)

## What Was Implemented
- `path/to/file` — what changed

## Files Read
- ...

## Verification
- Build: PASS · Lint: PASS/SKIPPED · Tests: PASS/SKIPPED

## Deviations from Plan
None | <what and why>

## Gaps Found
None | <description, which spec/design item is missing or contradictory>
```

## Process — fix mode
1. Read the report (`review-N-report.md` → Must-fix items; `verify-result.md` → Must and Should items), plus specs, design, plan-notes, and the actual files.
2. Fix only the reported issues. No refactors beyond them.
3. Verify (build / lint / test per profile, no regressions).
4. If a fix makes a previously checked task untrue, uncheck it and say so. If the report shows a scenario was never implemented and its task is checked, leave it checked only once the fix implements it.
5. Write `fix-N-<iter>-result.md` (review) or `fix-V-<iter>-result.md` (verify):

```markdown
# Fix Result: <summary>
_Change: <id> · Source: review-N | verify · Date: YYYY-MM-DD_
## Status: VERIFIED
## Issues Addressed
## What Was Changed
## Files Read
## Verification
```

## Rules
- Never edit proposal, specs, or design. A spec/design problem is a GAP.
- Never commit or push.
- Never tick a task you did not verify.
