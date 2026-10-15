# Architecture: openspec-worker

_Status: living contract — implemented in `plugins/openspec-worker/`. Edit alongside the SKILL.md files when behavior changes._
_Last updated: 2026-10-15 · Verified against OpenSpec CLI 1.14.2 (`@fission-ai/openspec`)_

`openspec-worker` is an autonomous pipeline that runs **on top of OpenSpec**. OpenSpec owns the artifact format, the living specs, validation, and archive. `openspec-worker` owns everything OpenSpec does not do: agent-driven interviews with expert routing and escalation, phased budgeted implementation, review/fix loops, verification, and the code map.

It is a single plugin. It is the OpenSpec-native sibling of `workflow` + `orchestrator-team-lead`, and shares no files or state with them.

---

## 1. Principles

1. **OpenSpec artifacts are the source of truth.** `proposal.md`, `specs/**`, `design.md`, `tasks.md` in `openspec/changes/<id>/` are canonical. Everything the worker writes there is valid OpenSpec, so a human can continue any change with `/opsx:*` at any point.
2. **Run state lives outside the change folder.** Interview history, results, reports and logs live in `.openspec-worker/runs/<id>/`. `openspec archive` moves the whole change folder, so anything placed inside it would be archived into permanent history.
3. **Read formats from the CLI, never hardcode them.** Every skill that writes an OpenSpec artifact first runs `openspec instructions <artifact> --change <id> --json` and follows the returned `instruction` and `template`. This keeps the plugin correct across OpenSpec versions.
4. **Read JSON, not exit codes.** `openspec archive --json` reports failure as `"archive": null` with a `status[]` array, not as a non-zero exit. Every CLI call the worker relies on uses `--json` and is parsed.
5. **The worker is its own gate.** `openspec archive --yes` archives a change even with unchecked tasks. The worker checks task completion, verification, and strict validation before it archives.
6. **Fresh agent per step; stop on escalation** — same as `orchestrator-team-lead`.

---

## 2. Directory layout

```
openspec/                               ← owned by OpenSpec
  config.yaml                           ← context/rules: worker writes a managed block (§5)
  specs/<capability>/spec.md            ← living specs (merged by archive)
  changes/<id>/
    .openspec.yaml  proposal.md  design.md  tasks.md  specs/<capability>/spec.md
  changes/archive/YYYY-MM-DD-<id>/

.openspec-worker/                       ← owned by openspec-worker
  profile.json                          ← project profile (§4)
  project-context.md                    ← optional free-text context
  code-map.json                         ← file index (same schema as orchestrator-team-lead)
  queue.md                              ← ordered work queue (§6)
  run-context.json                      ← run sentinel (exists only while a run is active)
  feature-briefs/NN-slug.md             ← source briefs copied from architector
  runs/<id>/                            ← per-change run state
    brief.md                            ← source brief (architector origin only)
    interview-history.json
    interview-questions.json            ← transient, current round
    routed-questions.json               ← transient, current round
    interview-answers.json              ← transient, current round
    expert-answers/<qid>.json           ← transient, one per expert
    interview-brief.md                  ← interview's final output
    escalation.md                       ← present while blocked; human answers go here
    spec-author-report.md
    plan-notes.md                       ← per-group budgets, files, contracts
    validation-report.md
    group-N-result.md
    review-N-report.md
    fix-N-<iter>-result.md
    verify-result.md
    fix-V-<iter>-result.md
    archive-summary.md
    run-log.md
  completed/<id>-YYYY-MM-DD/            ← runs/<id>/ moved here after archive
```

`<id>` is always the OpenSpec change id (kebab-case). Architector's `NN-slug` becomes change id `slug` (the `NN-` prefix is dropped; ordering lives in `queue.md`).

---

## 3. Artifact mapping

| Source | OpenSpec artifact | Written by |
|---|---|---|
| Architector brief: Goal, What Needs to Be Built, Out of Scope, Dependencies | `proposal.md` (Why / What Changes / Impact) | `bootstrap` / `enqueue` seeds a draft; `spec-author` finalizes |
| Architector brief: Key Decisions Already Made | `design.md` Decisions | `spec-author` |
| Architector brief: Open Technical Questions, Notes for interview | interview round-1 seed | `interview` reads `brief.md` |
| Interview Expected Behavior + Edge Cases | `specs/<capability>/spec.md` requirements + WHEN/THEN scenarios | `spec-author` |
| Interview Q&A (expert answers + rationale) | `design.md` Decisions (medium-confidence answers → alternatives considered) | `spec-author` |
| Deferrable open questions | `design.md` Open Questions | `spec-author` |
| Phased plan | `tasks.md` — **one `## N.` group per phase** | `plan` |
| Phase budgets, affected files, changed contracts | `runs/<id>/plan-notes.md` | `plan` |
| As-built: mental model, dependency map, deviations | appended `## As-built` section in `design.md` | `archive` |

`design.md` replaces `document-work-result`'s Decision Log; the `## As-built` section replaces its Mental Model and Dependency Map. Both are preserved in `openspec/changes/archive/<date>-<id>/design.md`.

---

## 4. Profile — `.openspec-worker/profile.json`

Same fields as `orchestrator-team-lead`'s profile, plus `openspec`:

```json
{
  "language": "typescript",
  "type_system": "strict",
  "contracts_first": true,
  "build": { "command": "pnpm build" },
  "lint":  { "command": "pnpm lint" },
  "test":  { "command": "pnpm test" },
  "patterns": { "error_handling": "Result types", "naming": "camelCase", "notes": "" },
  "code_map": { "enabled": true, "exclude": ["node_modules", "dist", ".git", "openspec", ".openspec-worker"] },
  "phase_token_budget": 130000,
  "phase_token_warn_at": 90000,
  "project_context_path": ".openspec-worker/project-context.md",
  "openspec": {
    "command": "openspec",
    "min_version": "1.14.0",
    "validate_strict": true
  }
}
```

`openspec.command` is the exact prefix used for every CLI call (e.g. `openspec` or `npx -y @fission-ai/openspec@1.14.2`). Skills never call a bare `openspec`; they use this value. In this document `$OS` stands for it.

---

## 5. `openspec/config.yaml` managed block

Bootstrap mirrors the profile into OpenSpec's own config so that **manual `/opsx:*` runs obey the same rules** as the worker. It writes only between markers and preserves everything else:

```yaml
# >>> openspec-worker (managed — edit .openspec-worker/profile.json instead)
context: |
  Language: typescript (strict types). Build: pnpm build. Lint: pnpm lint. Test: pnpm test.
  Error handling: Result types. Naming: camelCase.
rules:
  tasks:
    - Each numbered task group is one implementation phase and must be completable in a single fresh session.
    - Every task states how it is verified, using the project's build/lint/test commands where applicable.
operations:
  apply:
    guidance:
      - After finishing tasks by hand, run /openspec-worker:run so the code map is refreshed.
# <<< openspec-worker
```

If the user already has top-level `context:` / `rules:` / `operations:` keys outside the block, bootstrap merges into those keys instead of duplicating them, and reports what it changed.

---

## 6. Queue — `.openspec-worker/queue.md`

```markdown
# openspec-worker queue

| # | Change | Origin | Status | Notes |
|---|--------|--------|--------|-------|
| 1 | foundation | architector | done | |
| 2 | auth | architector | in-progress | |
| 3 | limit-title-length | manual | queued | entry: plan |
| 4 | export-csv | architector | blocked-needs-human | see runs/export-csv/escalation.md |
```

- **Origin**: `architector` (seeded from a brief) or `manual` (created by a human with `/opsx:propose` or `openspec new change`, added via `enqueue`).
- **Status**: `queued` · `in-progress` · `blocked-needs-human` · `done`.
- Order = execution order. Architector dependencies are respected by row order (bootstrap preserves the todo-list order).
- The worker only processes changes that are **in the queue**. Changes a human is still drafting are never picked up implicitly.

---

## 7. Entry-point detection (two-way handoff)

`run` decides where each change starts from the actual state, not from where it was created. It reads `$OS status --change <id> --json`, `$OS instructions apply --change <id> --json` (for `progress`), and the run folder:

| State observed | Entry step |
|---|---|
| `runs/<id>/escalation.md` with filled human answers | resume the step that escalated (§10) |
| Only `proposal.md` (no specs, no design) | **INTERVIEW (full)** |
| `proposal.md` + some of specs/design missing, or human-authored and no `interview-brief.md` | **INTERVIEW (gap mode)** — asks only about what is missing or ambiguous |
| `interview-brief.md` exists, planning artifacts incomplete | **SPEC-AUTHOR** |
| proposal + specs (+ design or design deliberately skipped) valid, no `tasks.md` | **PLAN** |
| `tasks.md` exists, no `plan-notes.md` | **PLAN (adopt mode)** — budgets existing groups, splits only overweight unchecked groups |
| `tasks.md` + `plan-notes.md`, unchecked tasks remain | **GROUP LOOP** from the first group with an unchecked task |
| All tasks checked, no `verify-result.md` with `DONE` | **VERIFY LOOP** |
| Verified | **ARCHIVE** |

Rules:
- The worker never rewrites a human-authored artifact wholesale. In gap/adopt modes it may add missing artifacts, add requirements/scenarios, fix validation errors, and split unchecked task groups. Every edit to a pre-existing artifact is listed in `spec-author-report.md` or `validation-report.md`.
- `design.md` is optional in OpenSpec (`/opsx:propose` may skip it). The worker creates it only if the interview produced decisions worth recording; otherwise it is skipped.
- Tasks checked by a human are trusted as done; `verify` audits them like any other work.

**Worker → human:** every artifact is standard OpenSpec. A human may stop the worker (or take a `blocked-needs-human` change) and continue with `/opsx:apply` / `/opsx:archive`. The managed `config.yaml` block keeps their manual run within the same rules. If they finish the change by hand, they should remove its queue row or mark it `done`.

---

## 8. Pipeline

```
preflight: profile.json, queue.md, $OS --version >= min_version, openspec/ root exists
write run-context.json
Task(code-map-update, mode=stale)     ← picks up any hand-made code changes since last run

for each queue row with status in (queued, in-progress), in order:
    status = in-progress; run-context.current_change = id
    entry = detect(id)                 ← §7

    INTERVIEW LOOP      (max_interview_rounds = 5)
    SPEC-AUTHOR         (internal validate/fix ≤ 3)
    PLAN                (internal validator ≤ 3, budget split ≤ 3)
    GROUP LOOP          per tasks.md group: implement → code-map-update → review → [fix → code-map-update] ≤ 3
    VERIFY LOOP         verify → [fix → code-map-update] ≤ 3
    ARCHIVE             gates → As-built → $OS archive → move runs/<id> → completed/

    status = done
remove run-context.json
```

### INTERVIEW LOOP
Identical protocol to `orchestrator-team-lead`: `interview` (Opus) writes either `interview-questions.json` (≤3 questions) or `interview-brief.md`; `router` (Haiku) writes `routed-questions.json`; one fresh `expert` (Opus) per question, run in parallel, each writing `runs/<id>/expert-answers/<qid>.json` (the run merges these files with a script instead of copying answer text through its own context); `low` confidence → ESCALATE; the run appends each round to `interview-history.json`.

Additions:
- `interview` reads **current behavior from the living specs** (`$OS list --specs --json`, `$OS show <spec> --type spec --json`) in addition to the brief and code map.
- Questions carry a `kind`. `kind: "capability"` questions ("does this belong in existing capability X or a new one; is it ADDED or MODIFIED?") are routed to a `spec-architecture` expert profile that is given the spec inventory.
- `interview-brief.md` gains a `## Capabilities` section and tags each Open Question `deferrable: yes|no`. Any `deferrable: no` question left after the final round → ESCALATE.

### SPEC-AUTHOR
`spec-author` (Opus) converts `interview-brief.md` + `interview-history.json` (+ `brief.md`) into `proposal.md`, `specs/<capability>/spec.md` deltas, and `design.md`, in dependency order, fetching `$OS instructions <artifact> --json` for each. Then runs `$OS validate <id> --strict --json` and fixes reported issues, max 3 rounds. Still invalid → writes `spec-author-report.md` with status `INVALID` → ESCALATE.

### PLAN
`plan` (Opus) writes `tasks.md` (per `$OS instructions tasks --json`) and `plan-notes.md`. Each `## N.` group is one phase and must fit `phase_token_budget` (same estimate formula and split strategies as `workflow:deep-plan` §10 of `architecture.md`). Each group lands its own tests. Writes `validation-report.md` with `APPROVED` / `NEEDS_REVISION` / `BUDGET_OVERRUN`; non-APPROVED → ESCALATE.

### GROUP LOOP
For group N: `implement group-N` (Sonnet) does the group's tasks, ticks `- [x]` in `tasks.md` for each task it completed and verified, writes `group-N-result.md`. A `GAP` status → ESCALATE. Then `code-map-update`, then `review group-N`; Must-fix items go to `implement fix`, max 3 iterations.

### VERIFY LOOP
`verify` (Opus) checks:
1. `$OS validate <id> --strict --json` passes.
2. `$OS instructions apply --json` → `progress.remaining == 0`.
3. **Every scenario** in the change's spec deltas is implemented and, if `profile.test` is non-null, covered by a test (scenario → file:line evidence table).
4. **Consistency**: names and behavior in specs, design and code agree (OpenSpec's validator only checks structure).
5. Integration audit, build/lint/test, regressions, Out-of-scope items not implemented.

`DONE` or `HAS_ISSUES` (Must/Should). Fixes via `implement fix`; max 3 iterations.

### ARCHIVE
`archive` (Sonnet) — gates (all must hold, otherwise ESCALATE): `verify-result.md` is `DONE`; `progress.remaining == 0`; strict validation passes. Then:
1. Append `## As-built` to `design.md` (Mental Model ≤1 page, Mermaid Dependency Map, Deviations from plan). Create `design.md` if it was skipped.
2. `$OS archive <id> --yes --json` → require `archive != null`. On null, record `status[]` in the log → ESCALATE (the CLI guarantees no files changed).
   Then apply **Purpose updates**: deltas cannot change an existing capability's Purpose, so `spec-author` (and `verify`) list proposed new Purposes under `## Purpose Updates`; `archive` writes them into `openspec/specs/<cap>/spec.md` directly, as OpenSpec's own instructions prescribe, and re-validates the specs.
3. Write `archive-summary.md` (goal, capabilities touched with added/modified/removed totals from the archive JSON, files changed).
4. Move `runs/<id>/` → `completed/<id>-YYYY-MM-DD/`.

---

## 9. Run sentinel — `run-context.json`

```json
{
  "mode": "autonomous",
  "current_change": "auth",
  "max_interview_rounds": 5,
  "iteration_caps": { "spec_author_validate": 3, "plan_validation": 3, "plan_split": 3, "review_fix": 3, "verify_fix": 3 }
}
```

All worker skills except `bootstrap` and `enqueue` are autonomous-only: they never prompt, read from `runs/<current_change>/`, write their outputs, and exit. If invoked without the sentinel they refuse and point to `/openspec-worker:run`.

---

## 10. Escalation and human answers

Triggers: expert `low` confidence; non-deferrable open question after the last interview round; spec-author still invalid after 3 rounds; plan not APPROVED; implement `GAP`; review or verify fix-loop cap hit; archive gate failed or `archive: null`; CLI version below minimum.

Action: queue row → `blocked-needs-human`; write `runs/<id>/escalation.md`; append to `run-log.md`; remove `run-context.json`; stop the whole run.

`escalation.md`:

```markdown
# Escalation: auth
_Step: interview round 2 · 2026-10-15T14:03:09Z_

## Reason
Expert q2 returned low confidence.

## Questions for a human
### q2: Should sessions survive a server restart?
Expert attempt: ... (confidence: low — rationale: ...)

#### Human answer
<!-- write your answer here, then re-run /openspec-worker:run -->
```

Non-interview escalations instead end with a `## Human resolution` checkbox (`- [ ] I fixed the cause above — resume this change on the next run`); the run resumes them only when it is ticked, never merely because there are no answer blocks.

On the next run, if every `#### Human answer` is filled, the run appends those answers to `interview-history.json` with `confidence: "human"` and resumes the interview loop. For non-interview escalations the human fixes the cause (edit artifacts, raise the budget, fix code) and simply re-runs; entry detection (§7) resumes at the right step. To abandon the worker for that change, the human continues with `/opsx:*` and removes the queue row.

---

## 11. Skills

| Skill | User-facing | Model | Purpose |
|---|---|---|---|
| `bootstrap` | yes | Sonnet | Check CLI, `openspec init`, profile, config.yaml block, architector briefs → changes + queue, code map |
| `enqueue` | yes | Sonnet | Add a hand-made change (or a new idea / brief file) to the queue |
| `run` | yes | Sonnet | Loop driver (§8) |
| `interview` | no | Opus | One interview round |
| `router` | no | Haiku | Route questions, build expert prompts |
| `expert` | no | Opus | Answer one question with confidence |
| `spec-author` | no | Opus | Interview → proposal/specs/design, strict-valid |
| `plan` | no | Opus | tasks.md groups + plan-notes.md, budget-checked |
| `implement` | no | Sonnet (Opus for verify fixes) | One group, or one fix |
| `review` | no | Sonnet | Code-quality review of one group |
| `verify` | no | Opus | Final audit against specs and design |
| `archive` | no | Sonnet | Gates, As-built, `openspec archive`, move run folder |
| `code-map-indexer` | no | Sonnet | Initial code map |
| `code-map-update` | no | Sonnet | Incremental map update (result-file mode or stale mode) |
| `profile-derive` | no | Sonnet | Draft profile from `.ai-arch/` |

---

## 12. Logging

`runs/<id>/run-log.md` — same table format as `orchestrator-log.md`:

```
| Time | Step | Model | Inputs | Outputs | Status |
```

Additionally every OpenSpec CLI call made by the run itself is logged with its command and the relevant JSON field (`valid`, `progress`, `archive.archivedAs`).

---

## 13. Known OpenSpec behaviors this design depends on (1.14.2)

| Behavior | Consequence |
|---|---|
| `status --json` is file-existence only | Entry detection also checks validity and run-folder state |
| `isPlanningComplete` includes `tasks`, so it is false until tasks.md exists | Entry detection routes on per-artifact status, never on `isPlanningComplete` |
| `archive --yes` ignores unchecked tasks | Worker gates on `progress.remaining == 0` |
| Archive failure = `"archive": null` + `status[]`, exit code not reliable | Parse JSON |
| `validate --strict` rejects MODIFIED blocks that drop existing scenarios, with fix instructions | spec-author self-fix loop |
| Validator does not check semantic consistency | `verify` step 4 |
| New capability deltas need `## Purpose` (≥50 chars) or main spec gets a TBD placeholder | Enforced via `instructions` text; verify checks |
| A delta cannot change an existing capability's Purpose | `## Purpose Updates` list → applied by archive to the main spec |
| A change with zero deltas is invalid unless `.openspec.yaml` has `skip_specs: true` | spec-author sets it only for pure refactor/tooling changes |
| Extra files inside a change folder are archived with it | Run state stays in `.openspec-worker/runs/` |
| `/opsx:apply` ticks tasks by `sourcePath`/`line` from `instructions apply --json` | Worker uses the same checkbox format, so both can share one tasks.md |

---

## 14. Open items

- Custom OpenSpec schema (`openspec schema fork`) with an explicit interview artifact — only needed if humans want to run the interview step through `/opsx:*` without the worker.
- `openspec store` support (`--store <id>`) for planning repos separate from the code repo.
- Seeding baseline specs for existing code areas when a change first touches them.
