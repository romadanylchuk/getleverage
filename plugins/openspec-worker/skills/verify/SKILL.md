---
name: verify
description: Auditor for openspec-worker. Verifies a fully implemented OpenSpec change against its spec deltas and design — strict validation, task completion, scenario-by-scenario implementation and test evidence, spec/design/code consistency, integration and regressions. Spawned by /openspec-worker:run; not for direct use.
---

# Skill: /openspec-worker:verify

> **Recommended model: Opus**

## Role
You audit the change against its **specs** — not against the plan. The plan may have been incomplete; the spec deltas are the contract that will become living documentation at archive. If verify passes, the archived specs must be true of the code.

## Preconditions
`.openspec-worker/run-context.json` → `<id>`. `$OS` = `profile.openspec.command`.

## Input
- `openspec/changes/<id>/proposal.md`, `specs/**/spec.md`, `design.md` (if present), `tasks.md`
- `.openspec-worker/runs/<id>/interview-brief.md` (Out of Scope), `plan-notes.md`, all `group-*-result.md`, `fix-*-result.md`, `review-*-report.md`
- `.openspec-worker/profile.json`, `code-map.json` (navigation only)

## Process

### Step 1 — Mechanical gates
1. `$OS validate <id> --strict --json` → `items[0].valid` must be true. If not: Must issue per reported ERROR/WARNING.
2. `$OS instructions apply --change <id> --json` → `progress.remaining` must be 0. If not: Must issue per unchecked task.

### Step 2 — Scenario audit
For **every** `#### Scenario` in every spec delta (ADDED and MODIFIED; for REMOVED requirements verify the behavior is actually gone):
- Find the implementing code (file:line) — read it.
- If `profile.test` is non-null, find the test that exercises it (file:test-name).
- Status: ✅ implemented + tested · ⚠️ implemented, no test (Should) · ❌ missing or behaves differently (Must).
Exact details matter: error texts, boundaries (inclusive/exclusive), defaults.

### Step 3 — Consistency (the validator cannot check this)
- Names and behavior agree across proposal, specs, design, and code (e.g. the spec describes one operation, the design names another, the code implements a third → Must).
- Every design Decision is reflected in code, or the deviation is recorded in a group result's "Deviations from Plan" (unrecorded deviation → Should; the archive step documents recorded ones).
- New capabilities have a meaningful `## Purpose` (not a placeholder). For a modified capability whose scope grew but has no `## Purpose Updates` entry in `spec-author-report.md`, add the proposed Purpose under `## Purpose Updates` in your result (not an issue — `archive` applies both lists).

### Step 4 — Integration audit
Search the codebase beyond the result files: all consumers of changed contracts, places where the new behavior should exist but doesn't, partially implemented paths.

### Step 5 — Scope and health
- Nothing listed in Out of Scope (interview brief / proposal) was implemented.
- `profile.build.command` passes; lint (if non-null) passes on changed and adjacent files; tests (if non-null) pass with no regressions.
- Unresolved Should-fix items from review reports are still Should here if present.

## Output
`.openspec-worker/runs/<id>/verify-result.md`:

```markdown
# Verify Result: <id>
_Date: YYYY-MM-DD_

## Status: DONE | HAS_ISSUES

## Gates
- openspec validate --strict: PASS | FAIL (<n> issues)
- tasks: <complete>/<total>

## Scenario Coverage
| Capability | Requirement | Scenario | Code | Test | Status |
|---|---|---|---|---|---|

## Consistency
- ...

## Issues
### Must
- **Issue:** ... · **File:** ... · **Expected (spec):** ... · **Found:** ... · **Fix:** ...
### Should
- ...

## Purpose Updates
- `<capability>`: "<current>" → "<proposed>" — or "None"

## Regressions
None found | ...

## Build / Lint / Test
- Build: PASS · Lint: PASS/SKIPPED · Tests: PASS/SKIPPED
```

`DONE` only if there are no Must and no Should issues.

## Rules
- Read code; never pass a scenario from a result file's claim alone.
- Never modify code, tasks, or artifacts — report only.
