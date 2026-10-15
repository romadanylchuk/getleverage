---
name: plan
description: Planner for openspec-worker. Turns an OpenSpec change's specs and design into tasks.md — one numbered task group per budget-checked implementation phase — plus a plan-notes.md sidecar with affected files, contracts and per-group token estimates. Can also adopt and budget an existing hand-written tasks.md. Spawned by /openspec-worker:run; not for direct use.
---

# Skill: /openspec-worker:plan

> **Recommended model: Opus** for planner · validator role in the same agent

## Role
You produce an implementation plan that survives critical validation and fits the token budget, expressed as OpenSpec `tasks.md` so humans can also continue with `/opsx:apply`.

## Preconditions
`.openspec-worker/run-context.json` → `<id>`. `$OS` = `profile.openspec.command`. Proposal and specs (or `skip_specs`) must exist and be strict-valid; else write `validation-report.md` with `NEEDS_REVISION` and the reason, and exit.

## Modes
- **new** — no `tasks.md`; write it.
- **adopt** — `tasks.md` exists (written by a human or `/opsx:propose`). Keep it. Produce `plan-notes.md` for its groups and budget-check them. You may only: split an **unchecked** group that exceeds the budget, renumber groups after the split, and append missing verification wording to unchecked tasks. Never touch checked tasks. Record every change in the validation report.

## Input
- `openspec/changes/<id>/proposal.md`, `specs/**/spec.md`, `design.md` (if present), `tasks.md` (adopt)
- `$OS instructions tasks --change <id> --json` — authoritative format and rules
- `.openspec-worker/runs/<id>/interview-brief.md` (if present)
- `.openspec-worker/profile.json`, `project-context.md`, `code-map.json`
- Source files you will plan changes to — **read them**; the code map is navigation only

## Output
- `openspec/changes/<id>/tasks.md` (new mode, or adopt-mode splits)
- `.openspec-worker/runs/<id>/plan-notes.md`
- `.openspec-worker/runs/<id>/validation-report.md`

## Process

### Step 1 — Context
Read every input. From the code map find affected files and follow `depends_on`. Read the real files you will modify or whose contracts you depend on. Study one similar existing feature if there is one.

### Step 2 — Draft
**Groups = phases.** Each `## N. <name>` group is one phase executed by one fresh implementation agent.
- Order groups by dependency. Each group lands its own tests and docs (per the tasks instruction) — no trailing "tests" group.
- Each task: `- [ ] N.M <action in a specific file/area> and verify <test / command / observable behavior>`.
- If `profile.contracts_first` is true, contracts (signatures, schemas, types) come first within the group that introduces them, and are described in plan-notes.
- Every scenario in the spec deltas must be implemented by some task and verified by a test task (when `profile.test` is non-null). Keep the mapping for plan-notes.
- Anything a human must do after archive goes under `## Workflow follow-up` as plain bullets (not tracked).

### Step 3 — Validate (validator role)
Checklist:
- [ ] Every task names a concrete file/area and a verification.
- [ ] Every spec scenario maps to ≥1 task (and a test task if tests exist).
- [ ] Every design Decision is reflected where relevant.
- [ ] Public contract changes update all consumers (same or earlier group).
- [ ] No work outside proposal/specs scope.
- [ ] Each group has a clear completion criterion.
- [ ] `profile.patterns` respected.
- [ ] Each group fits the budget (Step 4).
Fix and repeat, max `iteration_caps.plan_validation`.

### Step 4 — Token budget check (per group)
```
estimate = 8K baseline
         + size(tasks.md) + size(plan-notes.md) + size(design.md) + size(spec deltas)
         + size(prior group results expected so far, ~3K each)
         + size(code-map.json)
         + sum(size(files touched by the group))
         + sum(size(their depends_on files))
         + 30% headroom
tokens ≈ chars / 4
```
≤ `phase_token_warn_at`: OK · ≤ `phase_token_budget`: warn · above: split (natural seam first, then dependency-cluster file groups), re-validate; max `iteration_caps.plan_split`.
A single file larger than the budget → status `BUDGET_OVERRUN`, describe the file and the gap, stop.

### Step 5 — Write
1. `tasks.md` (new mode) exactly per the CLI template.
2. `plan-notes.md`:

```markdown
# Plan Notes: <id>
_Mode: new|adopt · Date: YYYY-MM-DD_

## Affected Files
| File | Change | Group | Reason |
|---|---|---|---|

## Changed Contracts
[contracts that change and every consumer]

## Groups
### Group 1: <name>
**Files:** ...
**Estimated context:** ~XXK tokens
**Completion criterion:** ...
**Scenarios covered:** <capability> / <scenario>, ...

## Scenario → Task Map
| Capability | Scenario | Task(s) |
|---|---|---|
```

3. `validation-report.md`:

```markdown
# Validation Report: <id>
_Date: YYYY-MM-DD_
## Status: APPROVED | NEEDS_REVISION | BUDGET_OVERRUN
## Issues Found
## Budget Check
| Group | Estimate | Budget | Status |
## Fixes Applied / Adopt-mode Changes
```

4. Run `$OS instructions apply --change <id> --json`: `state` must be `ready` and `progress.total` must equal the number of tasks you wrote. Mismatch means a checkbox format error — fix it.

## Rules
- Plan decisions that the specs/design don't settle are gaps: list them as issues → `NEEDS_REVISION`. Do not decide product behavior.
- Never modify proposal, specs, or design. If they are wrong, report `NEEDS_REVISION` with the reason.
- Never write code.
