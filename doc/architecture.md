# Architecture: workflow refactor + orchestrator-team-lead

_Status: living contract — implemented across the `workflow` and `orchestrator-team-lead` plugins. Edit alongside the SKILL.md files when behavior changes._
_Last updated: 2026-04-30_

This document is the design contract for two parts of the `getleverage` marketplace:

1. The `workflow` plugin — tech-agnostic and dual-mode (manual + autonomous).
2. The `orchestrator-team-lead` plugin — drives the workflow pipeline autonomously across a queue of feature briefs.

The `architector` plugin is independent. Its `.ai-arch/feature-briefs/` and `.ai-arch/todo-list.md` outputs are the orchestrator's input queue, copied into `.ai-work/feature-briefs/` and `.ai-work/todo-list.md` by `/orchestrator:bootstrap`.

---

## 1. Plugin layout

```
plugins/
  architector/              ← unchanged
  workflow/                 ← refactored: tech-agnostic, dual-mode
  orchestrator-team-lead/   ← new
```

---

## 2. Project profile — `.ai-work/profile.json`

The single source of truth for everything tech-specific. If a tool is absent, the field is `null` and skills skip the corresponding checks. Linter and tests are part of the project's architecture: if the project doesn't have them, the workflow doesn't pretend to run them.

```json
{
  "language": "typescript",
  "type_system": "strict",
  "contracts_first": true,

  "build":  { "command": "pnpm build" },
  "lint":   { "command": "pnpm lint" } | null,
  "test":   { "command": "pnpm test" } | null,

  "patterns": {
    "error_handling": "Result types",
    "naming": "camelCase functions, PascalCase types",
    "notes": "functional style preferred"
  },

  "code_map": {
    "enabled": true,
    "exclude": ["node_modules", "dist", ".next", "**/*.test.ts"]
  },

  "phase_token_budget": 130000,
  "phase_token_warn_at": 90000,

  "project_context_path": ".ai-work/project-context.md"
}
```

Field semantics:

- `type_system`: `"strict"` | `"loose"` | `"none"`. Drives whether `/workflow:review` runs the Types section.
- `contracts_first`: generic version of "types-first". When true, plans must define contracts (signatures, schemas, JSDoc, whatever the project uses) before implementation steps.
- `build.command`: always run by `/workflow:implement` verifier and `/workflow:review`.
- `lint.command`: run only if non-null. If null, lint check is skipped entirely.
- `test.command`: same rule.
- `patterns`: free-form notes that all skills inject into their context to enforce codebase consistency.
- `code_map.enabled`: opts in/out of the auto-maintained code index (see §6).
- `phase_token_budget`: hard ceiling for `/workflow:deep-plan`'s budget check (see §11).
- `phase_token_warn_at`: soft warning threshold (see §11).

---

## 3. Working directory layout

```
.ai-work/
  profile.json                    ← project-wide
  project-context.md              ← project-wide (optional notes)
  code-map.json                   ← project-wide (auto-maintained)
  todo-list.md                    ← project-wide queue (paths relative to .ai-work/)
  orchestrator-context.json       ← run-scoped sentinel

  feature-briefs/                 ← source briefs (read-only inputs)
    01-foundation.md              ← copied from architector or written by bootstrap
    02-auth.md
    ...

  briefs/                         ← active brief subfolders (one per in-flight brief)
    01-foundation/
      brief.md                    ← copy of source brief from feature-briefs/
      interview-history.json      ← all Q&A rounds accumulated
      interview-questions.json    ← current round's questions
      interview-answers.json      ← current round's answers
      interview-brief.md          ← final brief from interview
      feature-plan.md
      validation-report.md
      phase-1-result.md
      review-1-report.md
      fix-1-result.md
      phase-2-result.md
      ...
      final-check-result.md
      feature-docs.md
      orchestrator-log.md         ← per-step timestamped trail

  completed/
    01-foundation-2026-04-30/     ← compact-work output
```

### Path resolution

`todo-list.md` rows reference briefs by relative path (e.g. `feature-briefs/01-foundation.md`). All such paths are resolved relative to `.ai-work/`. The orchestrator's run loop, given a row, computes the source path as `.ai-work/<row.path>` and copies it to `.ai-work/briefs/<slug>/brief.md` at the start of that brief.

### File lifetime and ownership

| File | Lifetime | Updated by | Notes |
|------|----------|------------|-------|
| `profile.json` | project | bootstrap, manual edits | Persists forever |
| `project-context.md` | project | bootstrap, manual edits | Persists forever |
| `code-map.json` | project | bootstrap (initial), `code-map-update` (per phase) | Persists forever |
| `todo-list.md` | project | architector, bootstrap, orchestrator (status) | Persists forever |
| `feature-briefs/NN-slug.md` | project | bootstrap (copy from architector or ad-hoc write) | Persists for history |
| `orchestrator-context.json` | run | orchestrator | Created at run start, removed at run end |
| `briefs/NN-slug/` | brief | workflow skills | Archived by `compact-work` |
| `completed/NN-slug-DATE/` | archive | `compact-work` output | Persists for history |

**Hard rule:** `compact-work` MUST touch only `.ai-work/briefs/NN-slug/`. It MUST NOT touch any project-wide file.

---

## 4. Orchestrator sentinel — `orchestrator-context.json`

When a workflow skill starts and sees this file, it switches to autonomous behavior:

- No stdin prompts.
- Exit after writing output file(s).
- Route interview questions through the expert chain instead of asking the user.

```json
{
  "mode": "autonomous",
  "current_brief": "01-foundation",
  "max_interview_rounds": 5,
  "iteration_caps": {
    "review_fix": 3,
    "final_check_fix": 3,
    "plan_validation": 3,
    "deep_plan_split": 3
  }
}
```

If the file is absent, all workflow skills behave exactly as today — manual mode, interactive.

---

## 5. Code map — `.ai-work/code-map.json`

A lightweight auto-maintained index of the project's source files. Used for navigation by `/workflow:interview`, `/workflow:deep-plan`, `/workflow:implement`, `/workflow:review`, and `/workflow:final-check`. Designed to be too thin to substitute for reading actual files.

### Schema

```json
{
  "version": 1,
  "last_updated": "2026-04-30T14:02:11Z",
  "last_brief": "03-canvas",
  "patterns": {
    "error_handling": "Result<T, E>",
    "naming": "camelCase functions, PascalCase types",
    "layout": "src/<feature>/<file>.ts"
  },
  "files": {
    "src/auth/login.ts": {
      "summary": "Login form handler with OAuth fallback",
      "exports": ["loginUser", "validateCredentials"],
      "role": "feature",
      "depends_on": ["src/auth/session.ts", "src/api/client.ts"],
      "last_changed_in": "02-auth"
    }
  }
}
```

### What is NOT in the map

- No function signatures.
- No type definitions.
- No code snippets.

This is a deliberate constraint. The map is a phone book, not the contents of the book. If an agent needs to depend on a contract or modify a file, the map physically does not contain enough information — it must read the actual file.

### Lifecycle

- **Initial build (bootstrap):** if the project has source files and `code-map.json` does not exist, `/orchestrator:bootstrap` shows a token-cost estimate and asks the user "build code-map now (Y/N)?". If yes, spawns a one-shot indexing agent that walks the tree and produces the initial map.
- **Per-step update:** after every `/workflow:implement` and every `/workflow:implement fix` call, the orchestrator spawns `code-map-update`. It reads the just-produced result file (which lists changed/new files), updates only those entries. Cheap incremental update.
- **Drift detection:** if any agent reads a file and observes its exports differ from the map entry, it logs `code-map drift detected: <path>` and the next `code-map-update` invocation re-scans that file fully.
- **Manual rebuild:** `/orchestrator:rebuild-map` (utility command) for full rescan if needed.

### Verifier rule

`/workflow:implement` verifier and `/workflow:review` checklist gain one item:

> For every file modified or whose contract is depended on, did the agent's reads include the actual file (not only the map entry)?

If the agent's cited reads only show map entries for a file it changed, that's a fail and triggers another iteration.

---

## 6. Workflow plugin refactor — changes per skill

| Skill | Changes |
|-------|---------|
| `interview` | Drop KB step (Step 0). Tech-agnostic wording (no game/slot terms). **Autonomous mode**: read `interview-history.json`; output ≤3 questions to `interview-questions.json` OR final brief to `interview-brief.md`; exit. |
| `deep-plan` | Drop KB discovery (Step 1.2). Rename "types-first" → "contracts-first" (gated by `profile.contracts_first`). Validator references `profile`, not "TypeScript". **Add: Token Budget Check step** (see §11). Plan template gains per-phase `Estimated context` line. |
| `implement` | Verifier checklist driven by `profile`: `build.command` always; `lint.command` only if non-null; `test.command` only if non-null. No "TypeScript errors" / "ESLint" hardcoding. **New checklist item**: actual-file reads cited for changed/dependent files. **Autonomous mode**: exit after writing result. |
| `review` | Drop "any types" wording → "loose/escape-hatch types per profile". Skip Tests section if `profile.test == null`. Skip Types section if `profile.type_system == "none"`. Same actual-file-reads checklist item as `/workflow:implement`. |
| `final-check` | Drop KB. Generic wording. Autonomous-mode exit. |
| `document-work-result` | Drop KB. Generic wording. Autonomous-mode exit. |
| `compact-work` | Scope strictly limited to `.ai-work/briefs/NN-slug/` → `.ai-work/completed/NN-slug-DATE/`. Must not touch any project-wide file. |

_(`update-kb-document` was removed entirely in v2.0 — KB integration is replaced by `profile.json`, `project-context.md`, and `code-map.json`.)_

---

## 7. Orchestrator-team-lead plugin — new skills

### `/orchestrator:bootstrap`

The only interactive skill. Wizard for first-time setup or standalone use. Tries to derive as much as possible from architector output before asking the user.

Flow:

1. **Profile setup.** If `.ai-work/profile.json` does not exist:
   - **If `.ai-arch/` exists with decided/ready nodes:** spawn `profile-derive` helper agent (see below). It reads `.ai-arch/project-context.md` and all decided nodes, and produces a draft `profile.json` with field-by-field source attribution. Show the draft to the user with each field annotated:
     ```
     language: typescript           ← from tech-stack node
     type_system: strict            ← from tech-stack node
     build.command: pnpm build      ← from tooling node
     lint.command: <not decided>    ← please answer
     test.command: pnpm test        ← from testing node
     patterns.error_handling: Result types  ← from error-handling node
     ```
     Ask: "Confirm, edit any field, or fill missing fields?" Prompt only for fields marked `<not decided>` and for the orchestration-specific fields (`phase_token_budget`, `phase_token_warn_at`, `code_map.enabled`, `code_map.exclude`).
   - **If no `.ai-arch/`:** run the full wizard. Ask:
     - Project root path?
     - Language?
     - Type system (`strict` / `loose` / `none`)?
     - Build command?
     - Lint command? (or none)
     - Test command? (or none)
     - Notes on patterns (error handling, naming, etc.)?
     - Orchestration: `phase_token_budget` (default 130000), `code_map.enabled` (default true)?

   In both paths, build `profile.json`. Build `project-context.md` from `.ai-arch/project-context.md` (copy) or from a free-text "describe the project" answer if no architecture exists.

2. **Todo list setup.** If `.ai-arch/todo-list.md` exists, confirm reuse. If not, ask:
   - "Do you already have a feature description ready, or should I treat this as a single ad-hoc feature?"
   - If ad-hoc: short text → create a one-line todo list and a single `01-feature.md` brief.

3. **Code-map setup.** If `code-map.enabled` and project has source files but `code-map.json` does not exist:
   - Walk tree to estimate token cost.
   - Show estimate, ask "build code-map now (Y/N)?"
   - If yes: spawn one-shot indexer (Sonnet) → write `code-map.json`.

4. End with: "Bootstrap complete. Run `/orchestrator:run` to start the pipeline."

### `/orchestrator:run`

The team-lead loop driver. Stateless apart from `todo-list.md` and per-brief subfolders. Uses the Task tool to spawn fresh sub-agents for every pipeline step (the "clear context = new agent" mapping).

Behavior:

- Refuses to start if `profile.json` is missing → tells user to run `/orchestrator:bootstrap`.
- Writes `orchestrator-context.json` at start.
- Iterates over `todo-list.md` rows where status is `not started`.
- For each brief, walks the pipeline in §9.
- On any escalation, halts the entire run, updates the brief's status to `blocked-needs-human`, writes the reason to its log, and stops.
- On full success of a brief, marks it `done` in `todo-list.md` and proceeds to the next.
- At end of run (all briefs done or escalated), removes `orchestrator-context.json`.

### `/orchestrator:router`

Haiku. Classifies interview questions and builds tailored expert prompts.

Input: `interview-questions.json` + the brief's "Key Decisions Already Made" section.

For each question, emits:

```json
{
  "question": "...",
  "expert_profile": "frontend-react",
  "system_prompt": "You are an expert in React, the project uses ... Your job is to answer ONE question with confidence rating.",
  "context_files": ["src/components/Layout.tsx", "src/hooks/useAuth.ts"]
}
```

Output: `routed-questions.json`.

This combines router and prompt-creator in one agent. If we ever want to split them (separate "precreator"), it's a clean slice along the JSON boundary.

### `/orchestrator:expert`

Opus. Fresh agent per question — clean context every time. Reads its routed system prompt + listed context files + the one question. Outputs:

```json
{
  "question": "...",
  "answer": "...",
  "confidence": "high" | "medium" | "low",
  "rationale": "..."
}
```

Low confidence triggers escalation.

### Internal helper agent: `code-map-update`

Not user-facing. Spawned by `/orchestrator:run` after every `/workflow:implement` and `/workflow:implement fix` invocation. Reads the result file's "What Was Implemented" section, updates only the entries for changed/new files in `code-map.json`. Also handles drift re-scans flagged by other agents.

### Internal helper agent: `profile-derive`

Not user-facing. Spawned by `/orchestrator:bootstrap` when `.ai-arch/` exists and `.ai-work/profile.json` does not. Sonnet. Read-only against `.ai-arch/`.

Inputs:
- `.ai-arch/project-context.md`
- `.ai-arch/index.json`
- All `.ai-arch/ideas/*.md` files where the node is `decided` or `ready` (skip `raw-idea` and `explored` — their decisions aren't locked).

Process:
1. Read all decided/ready nodes' `## Decision` sections.
2. Map decisions to `profile.json` fields (see §13 mapping table).
3. For each field: if a confident value can be extracted, fill it. If multiple candidate values exist or the decision is vague, mark `<not decided>` and record the candidates in a comment for the user.
4. Copy `project-context.md` from `.ai-arch/` (or note it should be referenced).

Output: `.ai-work/profile.draft.json` plus a `profile-derive-report.md` showing source attribution per field. Bootstrap presents the draft to the user, accepts confirmation/edits, then writes the final `profile.json`.

No coupling in the other direction: architector remains unaware of `profile.json`. The derivation reads architecture as data, not as a contract.

---

## 8. Pipeline — control flow

```
load profile.json  (else: stop, "run /orchestrator:bootstrap first")
load todo-list.md
write orchestrator-context.json

for each not-done brief in todo-list:
    create .ai-work/briefs/NN-slug/, copy brief into brief.md
    log: "brief NN started"

    ── INTERVIEW LOOP (max 5 rounds) ──
    rounds = 0
    while rounds < 5:
        Task(Opus, interview)
        if interview-brief.md exists: break
        if interview-questions.json exists:
            Task(Haiku, router) → routed-questions.json
            for each routed question:
                Task(Opus, expert) → answer
                if answer.confidence == low: ESCALATE
            collect answers → interview-answers.json
            append round → interview-history.json
        rounds++
    if rounds == 5 without final brief: ESCALATE

    ── PLAN ──
    Task(Opus, deep-plan)
    if validation-report.status != APPROVED: ESCALATE
    if any phase fails token budget after split attempts: ESCALATE

    ── PHASE LOOP ──
    for each phase in feature-plan.md:
        iter = 0
        while iter < 3:
            Task(Sonnet, implement, phase=N)        → phase-N-result.md
            Task(Sonnet, code-map-update)           ← updates map for changed files
            Task(Sonnet, review, phase=N)           → review-N-report.md (reads UPDATED map)
            if review.must_fix == 0: break
            Task(Sonnet, fix, target=review-N-report.md)  → fix-N-result.md
            Task(Sonnet, code-map-update)           ← updates map again
            iter++
        if iter == 3 and review.must_fix > 0: ESCALATE

    ── FINAL-CHECK LOOP ──
    iter = 0
    while iter < 3:
        Task(Opus, final-check)                    → final-check-result.md (reads UPDATED map)
        if final-check.status == DONE: break
        Task(Opus, fix, target=final-check-result.md)  → fix-FN-result.md
        Task(Sonnet, code-map-update)
        iter++
    if iter == 3 and (must or should issues remain): ESCALATE

    ── DOCS + ARCHIVE (two separate agents, sequential) ──
    Task(Sonnet, document-work-result)
    Task(Sonnet, compact-work)

    mark brief done in todo-list.md
    log: "brief NN complete"

remove orchestrator-context.json
log: "all briefs done"
```

`ESCALATE` = update todo-list status to `blocked-needs-human`, write failure reason and last context to `orchestrator-log.md`, **stop the entire run**.

---

## 9. File contracts — per-skill I/O

All paths relative to `.ai-work/briefs/NN-slug/` unless noted.

| Skill | Reads | Writes |
|-------|-------|--------|
| `/workflow:interview` (autonomous) | `brief.md`, `interview-history.json`, `../../profile.json`, `../../project-context.md`, `../../code-map.json` | `interview-questions.json` OR `interview-brief.md` |
| `/orchestrator:router` | `interview-questions.json`, `brief.md` (Key Decisions section), `../../code-map.json` | `routed-questions.json` |
| `/orchestrator:expert` | One question from `routed-questions.json`, listed context files | One answer object (collected by orchestrator into `interview-answers.json`) |
| `/workflow:deep-plan` (autonomous) | `interview-brief.md`, prior phase results (none on first run), `../../profile.json`, `../../code-map.json` | `feature-plan.md`, `validation-report.md` |
| `/workflow:implement` (autonomous, phase=N) | `feature-plan.md`, `phase-(N-1)-result.md`, `../../profile.json`, `../../code-map.json`, source files for phase | `phase-N-result.md` |
| `code-map-update` | Latest `phase-N-result.md` or `fix-N-result.md`, current `../../code-map.json`, changed files for re-summarization | Updated `../../code-map.json` |
| `/workflow:review` (autonomous, phase=N) | `phase-N-result.md`, `feature-plan.md`, source files, `../../profile.json`, `../../code-map.json` | `review-N-report.md` |
| `/workflow:implement fix` | `review-N-report.md` OR `final-check-result.md`, `feature-plan.md`, `../../profile.json`, `../../code-map.json` | `fix-N-result.md` (review-driven) or `fix-FN-result.md` (final-check-driven) |
| `/workflow:final-check` (autonomous) | `interview-brief.md`, `feature-plan.md`, all `phase-*-result.md` and `fix-*-result.md`, `../../profile.json`, `../../code-map.json` | `final-check-result.md` |
| `/workflow:document-work-result` (autonomous) | All artifacts from this brief + source files, `../../profile.json` | `feature-docs.md` |
| `/workflow:compact-work` (autonomous) | Entire `briefs/NN-slug/` | Moves to `completed/NN-slug-DATE/`, leaves `briefs/NN-slug/` empty |

---

## 10. Token budget management

`/workflow:deep-plan` adds a Token Budget Check step after the validator approves the plan.

### Estimate formula (per phase)

```
phase_estimate =
    baseline (skill + profile + sentinel)               ~ 8K
  + feature-plan.md size                                  known
  + accumulated prior phase-result.md files               known
  + code-map.json size                                    known
  + sum of file sizes for "Affected Files" in phase       filesystem
  + sum of file sizes for files in their depends_on       from code-map
  + 30% headroom                                          for similar-impl reads,
                                                          verifier round, output, corrections
```

Token math: rough `chars / 4` is sufficient. Real tokenizer optional.

### Decision logic

For each phase:
- `estimate <= warn_at`: OK.
- `warn_at < estimate <= budget`: warn in plan output, do not split.
- `estimate > budget`: switch planner to split mode.

### Split strategies (in order)

1. **Natural split**: phase already does N logically distinct things → split along that seam (e.g., "phase 3a — schema migration", "phase 3b — API handlers").
2. **File-group split**: group files by dependency clusters; files sharing a contract change stay together.

Re-validate after each split. Cap at 3 split iterations.

### Single-file budget overrun

If a single file in a phase exceeds the budget, splitting can't help. `/workflow:deep-plan` writes a budget-overrun report and ESCALATES. The user must refactor the file (or raise the budget) before this brief can proceed. v1 does not attempt partial-file reads.

### Plan template addition

Each phase section gains:

```markdown
**Estimated context:** ~85K tokens
```

So humans reviewing the plan can spot phases at the edge.

---

## 11. Logging & observability

Every per-brief run writes `.ai-work/briefs/NN-slug/orchestrator-log.md`. Format:

```markdown
# Orchestrator Log: 01-foundation
_Started: 2026-04-30T14:02:00Z_

## Step Log
| Time | Step | Model | Skill | Inputs | Outputs | Status |
|------|------|-------|-------|--------|---------|--------|
| 14:02:11 | interview r1 | Opus | interview | brief.md | interview-questions.json | OK (3 questions) |
| 14:02:34 | router | Haiku | router | interview-questions.json | routed-questions.json | OK |
| 14:02:48 | expert q1 | Opus | expert | routed q1 | answer | OK (high) |
| 14:03:09 | expert q2 | Opus | expert | routed q2 | answer | LOW CONFIDENCE |
| 14:03:09 | run halted | — | — | — | — | ESCALATED |

## Escalation Reason
Expert q2 returned low confidence. Question: "..."
Answer attempted: "..."
Rationale: "..."

## Last State
Brief: 01-foundation
Phase context: pre-plan (interview round 1)
Files written: brief.md, interview-questions.json, routed-questions.json, interview-answers.json (partial)
```

Each row is one fresh agent invocation. The user can read this file at any time to see exactly where things stand.

---

## 12. Bootstrap flow (standalone use)

Triggered by `/orchestrator:bootstrap`. The only place in the entire orchestrator pipeline that talks to the user.

Decision tree:

```
profile.json exists?
  yes → skip profile setup

no profile.json:
  .ai-arch/ exists with decided/ready nodes?
    yes → spawn profile-derive helper:
          - reads project-context.md and decided nodes
          - produces profile.draft.json with source attribution
          - bootstrap shows draft to user with each field annotated:
              "language: typescript        ← from tech-stack node"
              "lint.command: <not decided> ← please answer"
          - user confirms / edits / fills missing fields
          - bootstrap also asks orchestration-specific fields
            (phase_token_budget, code_map.enabled, code_map.exclude)
          - write final profile.json
          - copy .ai-arch/project-context.md → .ai-work/project-context.md
    no  → run full wizard (8 quick questions covering profile fields
          + orchestration-specific fields + free-text project context)
          → write profile.json + project-context.md

todo-list.md exists?
  yes → confirm reuse, optionally update statuses
  no  → ask: "ad-hoc feature or describe project for ideation?"
        ad-hoc → ask for feature description, write 1-row todo-list and 01-feature.md brief
        ideation → tell user to use /architector first; exit

code-map.enabled true and source files exist?
  no map → estimate token cost, ask "build now (Y/N)?"
            yes → spawn one-shot indexer
            no  → mark code_map.enabled = false in profile, continue
  map exists → no action

end with: "Bootstrap complete. Run /orchestrator:run to start the pipeline."
```

### Profile derivation — field mapping

Used by the `profile-derive` helper agent when `.ai-arch/` is available.

| profile.json field | Architector source |
|---|---|
| `language` | `tech-stack` node, or any node with explicit language decisions |
| `type_system` | `tech-stack` decision (e.g., "TypeScript strict mode" → `"strict"`, "Python with mypy" → `"strict"`, "JavaScript" → `"none"`) |
| `contracts_first` | Inferred true if typed language chosen, false otherwise |
| `build.command` | `tech-stack` / `tooling` / `project-setup` node decisions |
| `lint.command` | `tooling` node, or any node naming a linter; null if no linter decided |
| `test.command` | `testing` / `qa` node, or any node naming a test runner; null if no testing decided |
| `patterns.error_handling` | `error-handling` node, `code-style` node, or notes in `project-context.md` |
| `patterns.naming` | `code-style` node, or `project-context.md` |
| `patterns.notes` | Free-form synthesis from `project-context.md` |
| `project_context_path` | `.ai-work/project-context.md` (copied from `.ai-arch/project-context.md`) |
| `phase_token_budget`, `phase_token_warn_at` | Not derivable — bootstrap asks user (defaults 130000 / 90000) |
| `code_map.enabled`, `code_map.exclude` | Not derivable — bootstrap asks user (defaults true / common patterns) |

The agent does not rely on hardcoded slug names. It reads all decided/ready nodes and classifies each `## Decision` block against the field set above. Vague or conflicting decisions are surfaced as `<not decided>` for the user to resolve.

After bootstrap, the user has everything `/orchestrator:run` needs to operate fully autonomously.

---

## 13. Escalation policy

Triggers (any of):

- Interview rounds exceed `max_interview_rounds` without producing a final brief.
- Any expert answer returns `confidence: low`.
- `/workflow:deep-plan` validator does not return APPROVED within `iteration_caps.plan_validation` rounds.
- `/workflow:deep-plan` token budget split fails after `iteration_caps.deep_plan_split` attempts (or single-file budget overrun).
- Phase review fix-loop exceeds `iteration_caps.review_fix` with `Must fix` issues remaining.
- Final-check fix-loop exceeds `iteration_caps.final_check_fix` with `Must` or `Should` issues remaining.

Action on escalation:

1. Update the brief's row in `todo-list.md`: status → `blocked-needs-human`.
2. Append escalation reason and last state to `orchestrator-log.md`.
3. Remove `orchestrator-context.json` (run is over).
4. Stop the entire run. Do not proceed to subsequent briefs.

Recovery: human reviews the brief's subfolder + log, makes changes (manual implementation, plan edits, profile adjustments), then re-runs `/orchestrator:run` which picks up where it left off (or skips this brief if marked done manually).

---

## 14. Model assignments

| Agent | Model |
|-------|-------|
| `interview` | Opus |
| `deep-plan` | Opus (planner) |
| `implement`, `review`, `fix` (per phase) | Sonnet |
| `final-check`, `final-check fix` | Opus |
| `document-work-result` | Sonnet |
| `compact-work` | Sonnet |
| `code-map-update` | Sonnet |
| `code-map` initial indexer | Sonnet |
| `profile-derive` | Sonnet |
| `/orchestrator:run` (team-lead loop) | Sonnet |
| `/orchestrator:bootstrap` | Sonnet |
| `/orchestrator:router` | Haiku |
| `/orchestrator:expert` | Opus (always, even for simple questions — quality of expert answers is critical) |

---

## 15. Open items / V2 considerations

Not in V1 but designed for future extension:

- **Code-map filtered views.** As `code-map.json` grows on large projects, agents may benefit from reading only the relevant slice (e.g., by directory or by relevance to the current phase). Schema is structured to allow this without migration.
- **External Agent SDK runner.** If we hit limits with the in-Claude Task tool model (e.g., need parallel briefs, persistent background runs), the same pipeline can be re-implemented as an SDK script. File contracts stay identical, so skills don't change.
- **Separate precreator agent.** Router currently combines classification + prompt creation. If prompt quality becomes an issue, splitting the precreator into its own agent is a clean change along the `routed-questions.json` boundary.
- **Symbol-level code-map.** Currently file-level only. Symbol-level (function → file) is higher maintenance. Add only if real navigation pain emerges.
- **Partial-file reads.** When a single file exceeds the phase token budget. Requires designing safe partial-read protocols. Out of scope for V1.
- **Run-resume.** Currently a halted run is restarted by re-running `/orchestrator:run` and skipping done briefs. A more granular resume (mid-brief, mid-phase) would require state checkpointing — V2 if needed.
- **Stack-overlay plugins.** If multi-stack projects become common, optional `workflow-typescript`, `workflow-python` overlay plugins can extend the generic workflow. The profile mechanism is the foundation; overlays would only add stack-specific patterns or verifier checks.

---

## 16. Implementation order

When we move to building this, recommended sequence:

1. **Workflow refactor** (drop KB, profile-driven verification, dual-mode wiring). Manual mode keeps working throughout.
2. **`code-map.json` and `code-map-update`** added to workflow as a pure addition (skills consult it if present, ignore if not).
3. **`/orchestrator:bootstrap`** in the new plugin.
4. **`/orchestrator:router` and `/orchestrator:expert`** — the two simplest sub-agents.
5. **`/orchestrator:run`** — the loop driver, building on (3) and (4).
6. **Token budget check** in `/workflow:deep-plan` — added once the rest is stable.

Each step ships independently usable: after (1) you have a tech-agnostic manual workflow; after (3) bootstrap is usable; after (5) the orchestrator works; after (6) it's complete.
