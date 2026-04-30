# orchestrator-team-lead

Autonomous team-lead that drives the `workflow` plugin's pipeline over a queue of feature briefs. Each pipeline step runs in a fresh agent with clean context (the "clear context = new agent" pattern). Coordination state lives in files; no agent accumulates context across steps.

## Pipeline (per brief)

```
interview-loop  (Opus interview ↔ Haiku router ↔ Opus expert per question)
deep-plan       (Opus, with token-budget split)
phase-loop      (Sonnet implement → Sonnet review → Sonnet fix [≤3])
final-check     (Opus, with fix-loop ≤3 on Must + Should)
document        (Sonnet)
compact         (Sonnet)
```

After every implement and every fix, a `code-map-update` agent refreshes `.ai-work/code-map.json` so the next agent sees newly created files.

## Skills

| Skill | Description | Model |
|-------|-------------|-------|
| `/orchestrator:bootstrap` | One-time interactive setup. Creates `.ai-work/profile.json` (deriving from architector output if available), todo-list, and optionally code-map. | Sonnet |
| `/orchestrator:run` | Main loop driver. Walks `todo-list.md` and runs the pipeline brief by brief. Stops on escalation. | Sonnet |
| `/orchestrator:router` | Classifies interview questions and builds tailored expert prompts. | Haiku |
| `/orchestrator:expert` | Answers one routed question with confidence rating. Fresh context per question. | Opus |

Internal helper agents (not user-invoked):

| Agent | Role |
|-------|------|
| `code-map-update` | Updates `code-map.json` for files touched by the latest implement/fix. |
| `code-map-indexer` | One-shot initial scan of the codebase to build `code-map.json`. |
| `profile-derive` | Reads `.ai-arch/` decided nodes and proposes a `profile.json` draft. |

## Quick start

```
# 1. Optional: run the architector first to produce feature briefs
/architector:new ...
/architector:finalize

# 2. Bootstrap the orchestrator (one-time)
/orchestrator:bootstrap

# 3. Run the pipeline
/orchestrator:run
```

If `.ai-arch/feature-briefs/` and `.ai-arch/todo-list.md` exist, the orchestrator consumes them. Otherwise bootstrap will ask for an ad-hoc feature description and create a single-brief queue.

## File layout

```
.ai-work/
  profile.json                    # project-wide
  project-context.md              # project-wide
  code-map.json                   # project-wide, auto-maintained
  todo-list.md                    # project-wide queue
  orchestrator-context.json       # run-scoped sentinel
  briefs/
    01-foundation/
      brief.md
      interview-history.json
      interview-questions.json
      interview-answers.json
      interview-brief.md
      feature-plan.md
      validation-report.md
      phase-1-result.md
      review-1-report.md
      fix-1-result.md
      ...
      final-check-result.md
      feature-docs.md
      orchestrator-log.md
  completed/
    01-foundation-2026-04-30/
```

## Escalation

The run halts and writes the reason to the brief's log when:

- Interview rounds exceed `max_interview_rounds` without producing a final brief.
- Any expert answer returns `confidence: low`.
- `/workflow:deep-plan` validator fails 3 times, or token budget cannot be split.
- A phase's review fix-loop exceeds 3 iterations with `Must fix` issues remaining.
- Final-check fix-loop exceeds 3 iterations with `Must` or `Should` issues remaining.

On escalation, the brief's status in `todo-list.md` becomes `blocked-needs-human`, the run stops, and the user picks up from the brief subfolder. Re-run `/orchestrator:run` once resolved.

## Relationship to other plugins

- **architector**: produces `.ai-arch/feature-briefs/` and `.ai-arch/todo-list.md` consumed by `/orchestrator:bootstrap` and `/orchestrator:run`.
- **workflow**: provides the per-step skills (interview, deep-plan, implement, review, final-check, document-work-result, compact-work). The orchestrator invokes these skills in autonomous mode by dropping `orchestrator-context.json`.

See [`doc/architecture.md`](../../doc/architecture.md) for the full design contract.
