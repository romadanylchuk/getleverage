# openspec-worker

Autonomous pipeline on top of [OpenSpec](https://github.com/Fission-AI/OpenSpec). OpenSpec gives you the artifact format, validation, and **living specs**; openspec-worker adds what OpenSpec doesn't have: agent-driven interviews with expert routing and escalation, budgeted phased implementation, review and verify loops, and a code map.

Every artifact it writes is standard OpenSpec, so any change can be handed back and forth between the worker and manual `/opsx:*` commands.

Full design contract: [doc/openspec-worker.md](../../doc/openspec-worker.md). Verified against OpenSpec CLI **1.14.2**.

## Install

```bash
claude plugin install openspec-worker@getleverage
```

## Requirements

- OpenSpec CLI ≥ 1.14.0: `npm i -g @fission-ai/openspec` (or let bootstrap use `npx`)
- Optional: architector output (`.ai-arch/`) as the source of feature briefs

## Quick start

```
/openspec-worker:bootstrap      ← once: CLI check, openspec init, profile, briefs → changes, code map
/openspec-worker:run            ← drive the queue autonomously
/openspec-worker:enqueue <id>   ← hand a manually created change to the worker
```

## Pipeline per change

```
INTERVIEW     interview (Opus) ⇄ router (Haiku) → expert (Opus) per question     max 5 rounds
                low confidence / non-deferrable open question → escalate to a human
SPEC-AUTHOR   interview-brief → proposal.md + specs/<cap>/spec.md + design.md
                self-fixes until `openspec validate --strict` passes             max 3
PLAN          tasks.md (one ## N. group = one budgeted phase) + plan-notes.md
GROUP LOOP    implement group-N → code-map-update → review → fix                 max 3 per group
VERIFY        strict validate + all tasks done + every scenario implemented/tested
                + spec/design/code consistency → fix                              max 3
ARCHIVE       gates → "As-built" section in design.md → `openspec archive`
                → deltas merged into openspec/specs/ (living documentation)
```

## Where things live

| Path | Owner | What |
|---|---|---|
| `openspec/changes/<id>/` | OpenSpec | proposal, specs deltas, design, tasks — canonical |
| `openspec/specs/` | OpenSpec | living specs, updated by archive |
| `openspec/config.yaml` | both | worker writes only a marked block mirroring your profile |
| `.openspec-worker/profile.json` | worker | language, build/lint/test, patterns, budgets, CLI command |
| `.openspec-worker/queue.md` | worker | ordered queue with status |
| `.openspec-worker/runs/<id>/` | worker | interview history, results, reports, run log, escalation |
| `.openspec-worker/completed/` | worker | run folders of archived changes |

## Handoff with manual OpenSpec work

**You → worker.** Create a change by hand (`/opsx:propose`, `openspec new change`), then `/openspec-worker:enqueue <id>`. The worker detects how far the change is and starts there:

| Change state | Worker starts with |
|---|---|
| proposal only | gap-mode interview (asks only what's missing) |
| proposal + specs (+ design) valid | plan |
| tasks.md written | plan in adopt mode (budgets your groups, never touches checked tasks) |
| tasks partly checked | the first unfinished group |
| all tasks checked | verify |

**Worker → you.** At any point — or when a change is `blocked-needs-human` — continue with `/opsx:apply <id>` / `/opsx:archive <id>`. The managed block in `openspec/config.yaml` makes the manual commands follow the same project rules. When you return, `/openspec-worker:run` refreshes the code map for code you changed by hand.

## Escalations

When the run halts it writes `.openspec-worker/runs/<id>/escalation.md`. For interview questions, write your answer under each `#### Human answer` and re-run `/openspec-worker:run` — your answers enter the interview history with `confidence: human` and the run resumes. For other escalations the file says what to fix; re-running resumes from the right step.

## Skills

| Skill | User-facing | Purpose |
|---|---|---|
| `/openspec-worker:bootstrap` | yes | One-time setup |
| `/openspec-worker:enqueue` | yes | Queue a manual change, description, or brief file |
| `/openspec-worker:run` | yes | Loop driver |
| `interview`, `router`, `expert` | no | Agent-driven interview |
| `spec-author` | no | Interview → valid OpenSpec artifacts |
| `plan` | no | tasks.md groups + budgets |
| `implement`, `review` | no | One group at a time, fix loop |
| `verify` | no | Audit against specs and design |
| `archive` | no | Gates, As-built, `openspec archive` |
| `code-map-indexer`, `code-map-update`, `profile-derive` | no | Helpers |

## OpenSpec behaviors the worker guards against

- `openspec archive --yes` archives even with unchecked tasks → the worker checks task completion itself.
- Archive failures return `"archive": null` in JSON rather than an error exit → parsed, not exit-code driven.
- The validator checks structure, not meaning → `verify` checks spec/design/code consistency and scenario coverage.

## Relationship to other plugins

Independent of `workflow` and `orchestrator-team-lead` (no shared files; state under `.openspec-worker/`). Consumes `architector` briefs the same way `orchestrator-team-lead` does.
