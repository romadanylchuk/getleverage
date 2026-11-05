---
name: archive
description: Archival agent for openspec-worker. Gates on verification, task completion and strict validation (openspec archive itself does not check tasks), appends an As-built section to design.md, runs openspec archive to merge spec deltas into the living specs, and moves the run folder to completed/. Spawned by /openspec-worker:run; not for direct use.
---

# Skill: /openspec-worker:archive

> **Recommended model: Sonnet**

## Role
Finish a verified change: document how it was actually built, merge its spec deltas into `openspec/specs/` via the CLI, and file the run history. This replaces `document-work-result` + `compact-work` of the `workflow` plugin.

## Preconditions
`.openspec-worker/run-context.json` → `<id>`. `$OS` = `profile.openspec.command`.

## Step 1 — Gates (all must pass; otherwise write `archive-summary.md` with `Status: BLOCKED` and the failed gate, and exit)
1. `.openspec-worker/runs/<id>/verify-result.md` exists with `Status: DONE`.
2. `$OS instructions apply --change <id> --json` → `progress.remaining == 0` and `progress.total > 0`. **Required: `openspec archive --yes` does not check this itself.**
3. `$OS validate <id> --strict --json` → `items[0].valid == true`.

## Step 2 — As-built section in design.md
Read `plan-notes.md`, every `group-*-result.md` and `fix-*-result.md`, and the changed source files. Append to `openspec/changes/<id>/design.md` (create it with a one-line `# Design` header and `## Context` "See proposal.md" if it was skipped):

```markdown
## As-built
_Archived by openspec-worker on YYYY-MM-DD_

### Mental Model
[≤1 page. Why the code is structured this way, the key abstractions, how the parts fit. For an engineer or agent meeting this code for the first time.]

### Dependency Map
```mermaid
graph TD
  ...feature boundary only...
```

### Deviations from Plan
[From group/fix results "Deviations from Plan" — or "None"]
```

Rules: document only what actually happened; never invent decisions; keep the map to the feature boundary.

Re-run `$OS validate <id> --strict --json` — the As-built section must not break validation.

## Step 3 — Archive
Run `$OS archive <id> --yes --json` and parse the JSON (do not rely on the exit code).
- `archive` is `null` → failure. Copy the `status[]` entries (code, message, fix) into `archive-summary.md` with `Status: FAILED` and exit. The CLI guarantees no files were changed.
- Otherwise record `archive.archivedAs` and `archive.totals` (added / modified / removed / renamed).

Confirm `openspec/changes/<id>/` is gone and `openspec/changes/archive/<archivedAs>/` exists. For every capability in the change, confirm `openspec/specs/<cap>/spec.md` exists and its Purpose is not a `TBD` placeholder.

**Purpose maintenance.** Deltas cannot change an existing capability's Purpose; OpenSpec's instructions say to edit the main spec directly. For each entry under `## Purpose Updates` in `spec-author-report.md` or `verify-result.md` (verify's wins on conflict), and for any capability whose Purpose is a `TBD` placeholder or plainly no longer covers its requirements after the merge, replace the text under `## Purpose` in `openspec/specs/<cap>/spec.md` (one or two sentences, 50+ chars, describing everything the capability now owns). Touch nothing else in the main spec. Then run `$OS validate --specs --strict --json` and require all valid. List each Purpose change in the summary.

## Step 4 — Summary
Write `.openspec-worker/runs/<id>/archive-summary.md`:

```markdown
# <change title>
_Archived: YYYY-MM-DD as `openspec/changes/archive/<archivedAs>/`_

## Status: ARCHIVED

## Goal
[1–2 sentences from proposal Why]

## Living Specs Updated
| Capability | Added | Modified | Removed | Renamed |
|---|---|---|---|---|

## Implementation Summary
[condensed from group results]

## Files Changed
[union of group and fix results]

## Follow-ups
[`## Workflow follow-up` bullets from tasks.md, TBD purposes, deferred Open Questions from design — or "None"]
```

## Step 5 — File the run
Move `.openspec-worker/runs/<id>/` → `.openspec-worker/completed/<id>-YYYY-MM-DD/` (append `-2`, `-3` if it exists). Do not touch anything else under `.openspec-worker/`.

## Rules
- Never call `$OS archive` before all gates pass; never use `--no-validate` or `--skip-specs` (unless `.openspec.yaml` has `skip_specs: true`, in which case the CLI handles it).
- Never edit `openspec/specs/` by hand — only via the CLI archive.
- Never touch `profile.json`, `queue.md`, `code-map.json`, `run-context.json`, or other changes.
- Do not commit or push.
