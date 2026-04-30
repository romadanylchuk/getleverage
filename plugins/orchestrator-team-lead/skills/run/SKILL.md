---
name: run
description: Autonomous team-lead loop driver. Walks the todo-list and runs the full workflow pipeline brief by brief, spawning fresh sub-agents per step via the Task tool. Use when the user says "run orchestrator", "start pipeline", "run team lead", or /orchestrator:run.
---

# Skill: /orchestrator:run

> **Recommended model: Sonnet**

## Role
You are the team-lead. Your job is to drive the workflow plugin's pipeline over the queue of feature briefs in `.ai-work/todo-list.md`. Every pipeline step runs in a **fresh sub-agent** spawned via the Task tool — you never accumulate phase-level context yourself. Your own state is just: which brief, which phase, which iteration.

## Hard rules

1. **Fresh agent per step.** Every `/workflow:interview`, `/workflow:deep-plan`, `/workflow:implement`, `/workflow:review`, fix, `/workflow:final-check`, `/workflow:document-work-result`, `/workflow:compact-work`, code-map-update, router, and expert call MUST be a separate Task invocation. Never run two steps in the same agent.
2. **State lives in files.** Read `.ai-work/profile.json`, `.ai-work/todo-list.md`, the brief subfolder, and the brief's `orchestrator-log.md`. Do not hold pipeline data in your own context.
3. **Stop on escalation.** Any failure that hits an iteration cap, low-confidence expert answer, or budget overrun → mark the brief `blocked-needs-human` in the todo-list, append the reason to the log, remove `orchestrator-context.json`, and stop the entire run.
4. **The user does not talk to you.** Bootstrap handled that. If `profile.json` is missing, refuse to start and tell the user to run `/orchestrator:bootstrap`.

## Preflight

Refuse to start if any of these are missing:
- `.ai-work/profile.json`
- `.ai-work/todo-list.md`

Refuse with: "Missing prerequisites. Run `/orchestrator:bootstrap` first."

If `.ai-work/orchestrator-context.json` already exists, ask:
> "A previous run is still in progress (sentinel file present). Resume from where it stopped, or reset and start fresh? (resume / reset / abort)"

- resume: read sentinel's `current_brief` and **restart that brief from the interview loop**. The sentinel does not store per-step state, so the loop relies on file existence to skip already-completed steps: if `interview-brief.md` is present, the interview loop short-circuits; if `feature-plan.md` is present, deep-plan is skipped; for each phase, the loop skips ahead to the highest existing `phase-N-result.md`. This makes resume idempotent without checkpointing.
- reset: remove sentinel, start over from the first not-done brief.
- abort: exit without changes.

## Sentinel

At run start, write `.ai-work/orchestrator-context.json`:

```json
{
  "mode": "autonomous",
  "current_brief": "<brief_slug>",
  "max_interview_rounds": 5,
  "iteration_caps": {
    "review_fix": 3,
    "final_check_fix": 3,
    "plan_validation": 3,
    "deep_plan_split": 3
  }
}
```

Update `current_brief` as the loop advances. Remove the file at run end.

---

## Path resolution

Every row in `todo-list.md` references its source brief by a path relative to `.ai-work/` (e.g. `feature-briefs/01-foundation.md`). Resolution rule:

```
source_path  = ".ai-work/" + row.path
target_path  = ".ai-work/briefs/" + slug + "/brief.md"
```

If `source_path` does not exist, treat the row as malformed and ESCALATE before doing any other work on it (`bootstrap` is responsible for ensuring all referenced briefs are physically present).

## Main loop

```
load profile.json
load todo-list.md  → list of briefs with status

for each brief in todo-list where status != "done":
    update sentinel.current_brief = brief.slug
    source_path = ".ai-work/" + brief.row.path
    target_dir  = ".ai-work/briefs/" + brief.slug + "/"
    if not exists source_path: ESCALATE("source brief missing: " + source_path)
    ensure target_dir exists
    if not exists target_dir/brief.md: copy source_path → target_dir/brief.md
    open log: target_dir/orchestrator-log.md
    log: "brief <slug> started"

    [INTERVIEW LOOP]   max 5 rounds
    [DEEP-PLAN]
    [PHASE LOOP]       per phase, max 3 fix iterations
    [FINAL-CHECK LOOP] max 3 fix iterations
    [DOCS]
    [ARCHIVE]

    update todo-list: brief.status = "done"
    log: "brief <slug> complete"

remove sentinel
log: "all briefs done"
```

---

## INTERVIEW LOOP

```
rounds = 0
while rounds < sentinel.max_interview_rounds:
    Task(model: Opus, skill: interview, brief: <slug>)
    log step: "interview round <rounds+1>"

    if exists briefs/<slug>/interview-brief.md:
        break  // interview is done

    if exists briefs/<slug>/interview-questions.json:
        Task(model: Haiku, skill: orchestrator:router, brief: <slug>)
            input: interview-questions.json + brief.md "Key Decisions Already Made"
            output: routed-questions.json
        log step: "router"

        for each routed question in routed-questions.json:
            Task(model: Opus, skill: orchestrator:expert)
                input: this question's system_prompt + context_files + question text
                output: an answer object with confidence rating
            log step: "expert q<id> -> confidence=<level>"
            if answer.confidence == "low":
                ESCALATE("expert q<id> low confidence: <rationale>")

        write briefs/<slug>/interview-answers.json with all answers
        append round to briefs/<slug>/interview-history.json:
          { round: <rounds+1>, questions: [...], answers: [...] }
        delete briefs/<slug>/interview-questions.json
        delete briefs/<slug>/interview-answers.json
    else:
        // No questions and no final brief — interview agent malfunction
        ESCALATE("interview round produced neither questions nor final brief")

    rounds++

if not exists briefs/<slug>/interview-brief.md:
    ESCALATE("interview did not produce a final brief within <max> rounds")
```

---

## DEEP-PLAN

```
Task(model: Opus, skill: deep-plan, brief: <slug>)
    input: interview-brief.md, profile.json, code-map.json
    output: feature-plan.md, validation-report.md
log step: "deep-plan"

read validation-report.md
if status == "BUDGET_OVERRUN":
    ESCALATE("token budget overrun: <reason from validation-report>")

if status != "APPROVED":
    ESCALATE("deep-plan validator failed: <issues>")
    // Note: deep-plan handles its own internal validator iterations and split iterations.
    // If it returns non-APPROVED, those caps were already hit.
```

---

## PHASE LOOP

```
read feature-plan.md → list of phases

for each phase N in 1..K:
    iter = 0
    while iter < sentinel.iteration_caps.review_fix:
        Task(model: Sonnet, skill: implement, brief: <slug>, args: "phase-<N>")
            output: phase-<N>-result.md
        log step: "implement phase-<N> iter <iter>"

        Task(model: Sonnet, skill: code-map-update, brief: <slug>)
            input: phase-<N>-result.md (or latest fix-result.md from this iter)
            output: updated .ai-work/code-map.json
        log step: "code-map-update"

        Task(model: Sonnet, skill: review, brief: <slug>, args: "phase-<N>")
            output: review-<N>-report.md
        log step: "review phase-<N> iter <iter>"

        read review-<N>-report.md
        if status == "PASSED" or no Must-fix items:
            break  // phase done

        Task(model: Sonnet, skill: implement, brief: <slug>, args: 'fix "<must-fix summary>"')
            input: review-<N>-report.md (Must-fix items only)
            output: fix-<N>-<iter>-result.md
        log step: "fix phase-<N> iter <iter>"

        Task(model: Sonnet, skill: code-map-update, brief: <slug>)
        log step: "code-map-update (post-fix)"

        iter++

    if iter == cap and review still has Must-fix:
        ESCALATE("phase <N> review fix-loop hit cap with Must-fix issues remaining")
```

---

## FINAL-CHECK LOOP

```
iter = 0
while iter < sentinel.iteration_caps.final_check_fix:
    Task(model: Opus, skill: final-check, brief: <slug>)
        output: final-check-result.md
    log step: "final-check iter <iter>"

    read final-check-result.md
    if status == "DONE":
        break

    // Issues remain — fix Must AND Should
    Task(model: Opus, skill: implement, brief: <slug>, args: 'fix "<issue summary>"')
        input: final-check-result.md (Must + Should items)
        output: fix-FN-<iter>-result.md
    log step: "fix from final-check iter <iter>"

    Task(model: Sonnet, skill: code-map-update, brief: <slug>)

    iter++

if iter == cap and final-check still has Must or Should issues:
    ESCALATE("final-check fix-loop hit cap with Must/Should issues remaining")
```

---

## DOCS

```
Task(model: Sonnet, skill: document-work-result, brief: <slug>)
    output: feature-docs.md
log step: "document-work-result"
```

---

## ARCHIVE

```
Task(model: Sonnet, skill: compact-work, brief: <slug>)
    moves briefs/<slug>/ → completed/<slug>-<date>/
log step: "compact-work"
```

After archive succeeds, the brief subfolder no longer exists. Update `todo-list.md` row: `status = done`.

---

## ESCALATE procedure

```
update todo-list.md row for current brief: status = "blocked-needs-human"
append to brief's orchestrator-log.md:
    ## Escalation
    Reason: <message>
    Last step: <last logged step>
    Files present: <ls of brief subfolder>
remove .ai-work/orchestrator-context.json
stop the entire run (do not proceed to next brief)
log to chat: "Run halted on brief <slug>: <reason>. See briefs/<slug>/orchestrator-log.md"
```

---

## Logging format

Each step appends a row to `.ai-work/briefs/<slug>/orchestrator-log.md`:

```
| 2026-04-30T14:02:11Z | implement phase-1 iter 0 | Sonnet | feature-plan.md | phase-1-result.md | OK |
```

Columns: timestamp | step | model | inputs (filenames, comma-separated) | outputs | status (OK / SKIPPED / ESCALATED).

At the top of the file, maintain a `## Step Log` table header. Append rows under it.

On escalation, append a `## Escalation` block with the reason and last state.

---

## Task tool usage

Each Task call should pass:
- `subagent_type`: prefer the workflow skill agent type if available, otherwise `general-purpose` with the skill explicitly invoked in the prompt.
- `model`: `opus`, `sonnet`, or `haiku` per the table in `doc/architecture.md` §14.
- `description`: short tag (e.g., "implement phase 1").
- `prompt`: a concise brief that:
  - Names the skill to run (e.g., "Run the `/workflow:implement phase-1` skill from the workflow plugin").
  - States the working directory and the brief slug.
  - Notes that `.ai-work/orchestrator-context.json` is present, so the skill must run in autonomous mode.
  - States the expected output file(s) the agent must produce.

Wait for each Task to complete. Verify expected output files exist before proceeding. If a Task returns without producing the expected output, treat that as a step failure and ESCALATE.

---

## Rules

- Never run two pipeline steps in one agent.
- Never silence or delete the orchestrator log.
- Never modify project-wide files (`profile.json`, `code-map.json`, `project-context.md`) directly — only via the helper agents.
- Never proceed past a missing expected output.
- Never accept user input mid-run (the user spoke at bootstrap; until escalation, this is autonomous).
