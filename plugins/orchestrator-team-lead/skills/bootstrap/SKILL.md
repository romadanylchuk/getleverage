---
name: bootstrap
description: One-time interactive setup for the autonomous orchestrator. Creates .ai-work/profile.json (deriving from .ai-arch/ if available), seeds the todo-list, and optionally builds code-map.json. Use when the user says "bootstrap", "setup orchestrator", "init orchestrator", or /orchestrator:bootstrap.
---

# Skill: /orchestrator:bootstrap

> **Recommended model: Sonnet**

## Role
You are the orchestrator's setup wizard. This is the only skill in the orchestrator plugin that talks to the user interactively. After bootstrap, `/orchestrator:run` operates fully autonomously.

## Goal
Produce three things, in priority order:
1. `.ai-work/profile.json` — project profile (drives all language/tooling decisions in the workflow)
2. `.ai-work/todo-list.md` — queue of feature briefs to implement
3. `.ai-work/code-map.json` — file index (optional but strongly recommended)

Plus copy/produce `.ai-work/project-context.md`.

---

## Process

### Step 1 — Profile setup

Check for `.ai-work/profile.json`.

**If it exists:** skip to Step 2. Confirm with the user:
> "Profile already exists. Skip to todo-list setup? (Y to skip, N to recreate)"

**If it does not exist:** decide the path based on architector availability.

#### Path A — Architecture-driven (preferred)
If `.ai-arch/` exists with at least one decided or ready node:

1. Spawn the `profile-derive` helper agent (skill in this plugin). Pass it the path to `.ai-arch/`. It produces:
   - `.ai-work/profile.draft.json`
   - `.ai-work/profile-derive-report.md` (source attribution per field)

2. Read both files. Show the draft to the user with each field annotated:
   ```
   language: typescript           ← from tech-stack node
   type_system: strict            ← from tech-stack node
   contracts_first: true          ← inferred (typed language)
   build.command: pnpm build      ← from tooling node
   lint.command: <not decided>    ← please answer
   test.command: pnpm test        ← from testing node
   patterns.error_handling: Result types ← from error-handling node
   patterns.naming: camelCase functions ← from code-style node
   ```

3. Ask the user, for fields marked `<not decided>`:
   > "Please fill in the missing field: <field>?"

4. Ask for orchestration-specific fields (these are never derivable):
   - `phase_token_budget` (default 130000)
   - `phase_token_warn_at` (default 90000)
   - `code_map.enabled` (default true)
   - `code_map.exclude` (default `["node_modules", "dist", ".next", ".git", "**/*.test.*"]`)

5. Ask:
   > "Confirm any field, or say 'edit <field> = <value>' to change."

6. Write final `.ai-work/profile.json`.
7. Copy `.ai-arch/project-context.md` → `.ai-work/project-context.md` if it exists.

#### Path B — Full wizard (no architecture)
If `.ai-arch/` does not exist or has no decided nodes, ask these questions one at a time:

1. "What language? (typescript / python / go / java / rust / javascript / other:___)"
2. "Type system? (strict / loose / none)"
3. "Build command? (e.g., 'pnpm build', 'cargo build', 'go build ./...')"
4. "Linter command, or 'none' if you don't run a linter? (e.g., 'pnpm lint')"
5. "Test command, or 'none' if you don't have tests? (e.g., 'pnpm test')"
6. "Error handling pattern? (free text — e.g., 'Result types', 'try/catch with custom errors', 'panic + recover')"
7. "Naming convention? (free text — e.g., 'camelCase functions, PascalCase types')"
8. "Anything else important about this project's style? (free text — short paragraph for `project-context.md`)"

Then ask for orchestration-specific fields (same as Path A step 4).

Construct the profile and write `.ai-work/profile.json`. Write the free-text answer to step 8 as `.ai-work/project-context.md`.

**Profile schema (full):**
```json
{
  "language": "typescript",
  "type_system": "strict",
  "contracts_first": true,
  "build":  { "command": "pnpm build" },
  "lint":   { "command": "pnpm lint" } | null,
  "test":   { "command": "pnpm test" } | null,
  "patterns": {
    "error_handling": "...",
    "naming": "...",
    "notes": "..."
  },
  "code_map": { "enabled": true, "exclude": [...] },
  "phase_token_budget": 130000,
  "phase_token_warn_at": 90000,
  "project_context_path": ".ai-work/project-context.md"
}
```

Note: `contracts_first` defaults to `true` for typed languages (`type_system != "none"`), `false` otherwise. The user can override.

---

### Step 2 — Todo-list and feature-briefs setup

**Canonical layout.** Source briefs always live at `.ai-work/feature-briefs/NN-slug.md`. `.ai-work/todo-list.md` rows reference briefs by relative path (e.g. `feature-briefs/01-foundation.md`); paths resolve relative to `.ai-work/`. The orchestrator copies each brief into `.ai-work/briefs/<slug>/brief.md` at run time.

Check for `.ai-arch/todo-list.md`, `.ai-arch/feature-briefs/`, and `.ai-work/todo-list.md`.

**If `.ai-work/todo-list.md` exists:** confirm reuse. Optionally offer to reset statuses to `not started` for re-runs. Verify each referenced brief exists at `.ai-work/<row.path>`; if any are missing, surface the gap.

**If only `.ai-arch/todo-list.md` exists:**
1. Copy `.ai-arch/todo-list.md` → `.ai-work/todo-list.md`, preserving statuses. The relative paths inside (e.g. `feature-briefs/01-foundation.md`) remain unchanged because the layout mirrors `.ai-arch/`.
2. Copy every file in `.ai-arch/feature-briefs/` → `.ai-work/feature-briefs/`. This is required so the relative paths in the copied todo-list resolve under `.ai-work/`.
3. Confirm with the user.

**If neither exists:** ask:
> "No todo-list found. Do you want to:
> (1) Run the architector to produce feature briefs (recommended for new projects)
> (2) Treat this as a single ad-hoc feature — describe it now and I'll create a single-brief queue"

If (1): tell the user to run the architector pipeline (`/architector:new` → `/architector:triage` → `/architector:explore` → `/architector:decide` → `/architector:finalize`), then re-run `/orchestrator:bootstrap`. Exit.

If (2): ask for the feature description. Create:
- `.ai-work/feature-briefs/01-feature.md` (using the architector's feature brief template, with all decisions left as Open Questions)
- `.ai-work/todo-list.md` with one row pointing at `feature-briefs/01-feature.md`.

---

### Step 3 — Code-map setup

If `profile.code_map.enabled` is false, skip this step.

If `.ai-work/code-map.json` already exists, skip.

Otherwise:
1. Walk the project root (respecting `profile.code_map.exclude`) and count source files plus their total size in characters.
2. Estimate token cost: `(total_chars / 4) * 1.5` (the indexer reads files plus generates summaries).
3. Show the estimate to the user:
   > "Building the code-map will scan N files (~XK tokens). Build now? (Y / N / change-excludes)"

4. If Y: spawn the `code-map-indexer` helper agent. Wait for it to write `.ai-work/code-map.json`.
5. If N: set `profile.code_map.enabled = false` and update `profile.json`. Continue.
6. If change-excludes: ask for new exclude patterns, update `profile.json`, retry estimate.

---

### Step 4 — Final summary

End with:
> "Bootstrap complete.
>
> Profile: `.ai-work/profile.json`
> Todo-list: `.ai-work/todo-list.md` (N briefs)
> Code-map: `.ai-work/code-map.json` (or 'disabled')
>
> Run `/orchestrator:run` to start the pipeline."

---

## Rules

- This skill is the only place in the orchestrator that prompts the user. Never accept stdin in any other orchestrator skill.
- Profile values must be valid: build/lint/test commands must be real shell commands or null; `type_system` must be `strict`/`loose`/`none`; tokens must be positive integers.
- Never overwrite an existing `profile.json` without explicit user confirmation.
- Never overwrite an existing `code-map.json` — that's the job of `/orchestrator:rebuild-map` (future utility).
- If anything fails (architector folder unreadable, etc.), surface the error clearly and let the user decide whether to fall back to Path B or abort.
