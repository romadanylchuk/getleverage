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
- `profile.build.command` passes; lint (if non-null) passes on changed and adjacent files.
- Tests (if non-null): this is the regression gate for the whole change, because implement and fix steps only ran scoped tests.
  - `profile.test.verify` set (a non-empty list of commands): run **every** command in the list, in order, one at a time, with nothing else running alongside. A failing command does not stop the rest.
  - Otherwise: run the full suite, `profile.test.command`, once.
  - The profile alone decides what runs. Do not skip, narrow or reorder commands or add exclusions, even if your prompt says to.
  - Do not re-run a command to confirm a single fix or a suspected flake; run that test file alone.
  - **Carrying a result from the previous iteration.** When an earlier `verify-result.md` of this change lists a command as PASS with its start time, and no file in the working tree (tracked or untracked, ignoring `.openspec-worker/` and `openspec/`) was modified after that start time, do not run the command again: list it as `PASS (carried from iter <n>)` with the original start time. A command that failed, was not finished, or has any newer file is run again. Check the times with the file system (`git ls-files -co --exclude-standard` plus `stat`), not from a result file's claim.
  - A command that could not finish (killed, out of memory, crashed runner) is not a pass. Run it once more on its own. If it still cannot finish, set status `INCOMPLETE` and list it under `## Tests Not Finished`. Do not run it again.
- Unresolved Should-fix items from review reports are still Should here if present.

## Running commands
- Before any build, lint or test command, set every variable in `profile.env` (bash `export K='V'`, PowerShell `$env:K='V'`).
- Run build, lint and test commands in the foreground and pass the shell tool's `timeout` parameter (600000 ms). Without it, a command that runs past the default timeout is moved to the background.
- If a command still ends up in the background, or needs more than 10 minutes, wait for it **inside this turn**: use the Monitor tool, or wait for its completion notice and then read its output file. **Never end your turn while a command you started is still running** — the run cannot resume you, and the pipeline stalls until a human notices.
- Do not write your own wait loops in the shell (`sleep`, `until …; do sleep`, `timeout … tail -f /dev/null`).
- A failure you can show is unrelated to this change (it fails the same way with the change's edits absent, or it is an environment problem named in the output) is listed under `## Regressions` as pre-existing with that evidence; it is not a Must issue.

## Output
`.openspec-worker/runs/<id>/verify-result.md`:

```markdown
# Verify Result: <id>
_Date: YYYY-MM-DD_

## Status: DONE | HAS_ISSUES | INCOMPLETE

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

## Tests Not Finished
None | <command> — <how it ended>

## Build / Lint / Test
- Build: PASS · Lint: PASS/SKIPPED · Tests (full | list): PASS/FAIL/SKIPPED — <counts>
- <with a list, one line per command: command — PASS/FAIL/PASS (carried from iter <n>) — counts — started <ISO time>>
```

`DONE` only if there are no Must and no Should issues and every test command finished. `INCOMPLETE` if any test command could not finish; a code fix cannot solve that, so report any issues you found as usual and let the run escalate. A Should issue is one the archived specs do not depend on: a scenario that is implemented and tested but a wording, structure, documentation or test-depth point remains. Anything the specs or design require is a Must. The run fixes Should issues only when `profile.verify_fix_should` is true; otherwise `archive` files them as follow-ups.

## Rules
- Read code; never pass a scenario from a result file's claim alone.
- Never modify code, tasks, or artifacts — report only.
- Never end your turn while a command you started is still running.
