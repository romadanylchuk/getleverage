---
name: bootstrap
description: One-time interactive setup for openspec-worker in a project. Checks the OpenSpec CLI, runs openspec init if needed, creates .openspec-worker/profile.json (derived from .ai-arch/ when available), writes the managed block in openspec/config.yaml, turns architector feature briefs into OpenSpec changes and a queue, and optionally builds the code map. Use when the user says "bootstrap openspec worker", "setup openspec worker", or /openspec-worker:bootstrap.
---

# Skill: /openspec-worker:bootstrap

> **Recommended model: Sonnet**

## Role
You are the setup wizard. Together with `enqueue`, this is the only interactive skill in the plugin. After bootstrap, `/openspec-worker:run` works autonomously.

Design contract: `doc/openspec-worker.md`.

## Goal
1. A working OpenSpec CLI and an initialized `openspec/` root.
2. `.openspec-worker/profile.json` (+ optional `project-context.md`).
3. A managed block in `openspec/config.yaml` mirroring the profile.
4. `.openspec-worker/queue.md` with one OpenSpec change per architector brief (or an ad-hoc change).
5. `.openspec-worker/code-map.json` (optional).

Re-running bootstrap is safe: each step detects existing output and asks before changing it.

---

## Step 1 — OpenSpec CLI

1. Try `openspec --version`. If it fails, try `npx -y @fission-ai/openspec --version`.
2. Neither works → tell the user:
   > "OpenSpec CLI not found. Install it with `npm i -g @fission-ai/openspec` (Node 20.19+), then re-run bootstrap. Or say 'use npx' to run it through npx every time (slower)."
   Stop unless they choose npx.
3. Version must be ≥ 1.14.0 (the version this plugin was verified against). Lower → ask the user to upgrade; stop.
4. Remember the working prefix as `$OS` (`openspec`, or `npx -y @fission-ai/openspec@<version>` pinned to the detected version).

## Step 2 — OpenSpec root

Run `$OS list --json`.
- `root` present → already initialized. Continue.
- `root` null → ask:
  > "This project has no OpenSpec root. Run `openspec init --tools claude` here? (Y/N)"
  On Y run `$OS init --tools claude --no-animation .`. This also installs the `/opsx:*` commands for manual work. On N stop — the worker cannot run without OpenSpec.

## Step 3 — Profile

If `.openspec-worker/profile.json` exists: ask "Profile exists. Keep it? (Y to keep / N to recreate)".

Otherwise build it exactly as `orchestrator-team-lead`'s bootstrap does:

**Path A — architecture available** (`.ai-arch/` with decided/ready nodes): spawn the `profile-derive` helper (Task, Sonnet). It writes `.openspec-worker/profile.draft.json` and `.openspec-worker/profile-derive-report.md`. Show the draft annotated with sources, ask for every `<not decided>` field, then the orchestration fields.

**Path B — no architecture**: ask one at a time: language; type system (strict/loose/none); build command; lint command or none; test command or none; error-handling pattern; naming convention; free-text style notes (→ `project-context.md`).

**Orchestration fields** (both paths): `phase_token_budget` (default 130000), `phase_token_warn_at` (default 90000), `code_map.enabled` (default true), `code_map.exclude` (default `["node_modules", "dist", "build", ".git", "openspec", ".openspec-worker", "**/*.test.*"]`).

Add the `openspec` block:
```json
"openspec": { "command": "<$OS>", "min_version": "1.14.0", "validate_strict": true }
```

Show the final profile, accept `edit <field> = <value>`, then write `.openspec-worker/profile.json`. Copy `.ai-arch/project-context.md` → `.openspec-worker/project-context.md` if it exists. Delete the draft files.

## Step 4 — `openspec/config.yaml` managed block

Read `openspec/config.yaml`. Build the block:

```yaml
# >>> openspec-worker (managed — edit .openspec-worker/profile.json instead)
context: |
  Language: <language> (<type_system> types). Build: <build>. Lint: <lint or "none">. Test: <test or "none">.
  Error handling: <patterns.error_handling>. Naming: <patterns.naming>.
  <patterns.notes, one line, if any>
rules:
  tasks:
    - Each numbered task group is one implementation phase and must be completable in a single fresh session.
    - Every task states how it is verified, using the project's build/lint/test commands where applicable.
operations:
  apply:
    guidance:
      - After finishing tasks by hand, run /openspec-worker:run so the worker's code map is refreshed.
# <<< openspec-worker
```

- If the markers already exist, replace only the text between them.
- If the file has uncommented top-level `context:`, `rules:` or `operations:` keys outside the markers, do **not** create duplicate keys: merge the worker lines into the existing keys instead (append to the `context` text, append list items), wrap each inserted line group with `# openspec-worker` comments, and show the user the diff before writing.
- Validate the result parses as YAML (e.g. `node -e "require('fs')..."` is not enough — re-run `$OS status --change <any> --json` or `$OS list --json` and confirm no config error is reported).

## Step 5 — Queue and changes

Check `.openspec-worker/queue.md`.

**Exists:** show it; offer to (a) keep, (b) reset `blocked-needs-human` rows to `queued`, or (c) import new architector briefs not yet in it. Then go to Step 6.

**Missing, and `.ai-arch/todo-list.md` + `.ai-arch/feature-briefs/` exist:**
1. Copy every brief to `.openspec-worker/feature-briefs/`.
2. For each todo-list row, in order:
   - `id` = the brief slug without the `NN-` prefix (kebab-case). If `openspec/changes/<id>/` already exists, ask: reuse it, or use `<id>-2`.
   - `$OS new change <id> --description "<brief title>" --json` (skip if reusing).
   - Seed `openspec/changes/<id>/proposal.md` from the brief, following `$OS instructions proposal --change <id> --json` (template + instruction):
     - **Why** ← brief Goal
     - **What Changes** ← brief What Needs to Be Built (bullets)
     - **Capabilities** ← leave both lists with a single line `- (to be decided by interview)`; the interview and spec-author decide them
     - **Impact** ← brief Context (affected parts) + Dependencies
   - Create `.openspec-worker/runs/<id>/brief.md` as a copy of the source brief (the interview reads Key Decisions, Open Technical Questions, Out of Scope, Notes for interview from it).
   - Add a queue row: origin `architector`, status `queued` (or `done` if the todo-list row is done — then do not create a change at all).
3. Show the resulting queue and the created change folders.

**Missing, no architector output:** ask:
> "No feature briefs found. (1) Run the architector first (`/architector:new` … `/architector:finalize`), then re-run bootstrap. (2) Add work now: describe a feature, or name existing OpenSpec changes to queue."
- (1): exit.
- (2): hand over to the `enqueue` procedure (same steps as `/openspec-worker:enqueue`) for each item, then write the queue.

Queue format (`.openspec-worker/queue.md`):

```markdown
# openspec-worker queue

| # | Change | Origin | Status | Notes |
|---|--------|--------|--------|-------|
| 1 | foundation | architector | queued | |
```

## Step 6 — Code map

Same as `orchestrator-team-lead` bootstrap Step 3, with paths under `.openspec-worker/`:
- skip if `code_map.enabled` is false or `code-map.json` exists;
- estimate `(total_chars / 4) * 1.5` over non-excluded source files, ask "Build now? (Y / N / change-excludes)";
- Y → spawn `code-map-indexer` (Task, Sonnet); N → set `code_map.enabled = false` in the profile.

## Step 7 — Summary

> "Bootstrap complete.
> OpenSpec: <version> via `<$OS>` · root `openspec/`
> Profile: `.openspec-worker/profile.json` (mirrored into `openspec/config.yaml`)
> Queue: `.openspec-worker/queue.md` (N changes)
> Code map: built / disabled
>
> Run `/openspec-worker:run` to start. Hand-made changes can be added any time with `/openspec-worker:enqueue <change-id>`."

## Rules
- Never overwrite `profile.json`, `queue.md`, `code-map.json`, or an existing change's artifacts without explicit confirmation.
- Never edit `openspec/config.yaml` outside the managed markers except for the confirmed merge in Step 4.
- Never write `specs/`, `design.md` or `tasks.md` — only the seeded `proposal.md`.
- If a step fails, show the error and let the user choose: retry, skip the step, or abort.
