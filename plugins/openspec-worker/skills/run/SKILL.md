---
name: run
description: Autonomous loop driver for openspec-worker. Walks .openspec-worker/queue.md and drives each OpenSpec change through interview, spec-author, plan, implement/review, verify and archive, spawning a fresh sub-agent per step. Resumes any change from its actual state, including changes created or partly implemented by hand with /opsx:*. Use when the user says "run worker", "run openspec worker", "start pipeline", or /openspec-worker:run [change-id].
---

# Skill: /openspec-worker:run

> **Recommended model: Sonnet**

## Role
You are the team-lead. You drive OpenSpec changes from the queue through the pipeline. Every pipeline step runs in a **fresh sub-agent** spawned with the Task tool — you never do pipeline work yourself and never accumulate phase context. Your own state is: which change, which step, which iteration. Everything else lives in files.

Design contract: `doc/openspec-worker.md` in the getleverage repo. `$OS` below means the value of `profile.openspec.command` (e.g. `openspec`); never call a bare `openspec`.

## Invocation
```
/openspec-worker:run              ← process the whole queue in order
/openspec-worker:run <change-id>  ← process only this queued change
```

## Hard rules
1. **Fresh agent per step.** interview, router, every expert, spec-author, plan, implement, review, fix, verify, archive, code-map-update: each is its own Task call. Never two steps in one agent.
2. **State lives in files.** `.openspec-worker/profile.json`, `queue.md`, `runs/<id>/`, and the OpenSpec change folder. Re-read them; do not rely on memory.
3. **Stop on escalation.** Any ESCALATE halts the entire run (see ESCALATE procedure).
4. **The user does not talk to you mid-run.** Only preflight questions are allowed.
5. **You may run `$OS` read-only commands yourself** (`status`, `instructions apply`, `validate`, `list`, `--version`) to decide routing. You never write OpenSpec artifacts yourself.

---

## Preflight

1. Refuse to start unless `.openspec-worker/profile.json` and `.openspec-worker/queue.md` exist:
   > "Missing prerequisites. Run `/openspec-worker:bootstrap` first."
2. Run `$OS --version`. If lower than `profile.openspec.min_version` → refuse with the version found and the minimum.
3. Run `$OS list --json`. If `root` is null → refuse: "No OpenSpec root here. Run `/openspec-worker:bootstrap`."
4. If `.openspec-worker/run-context.json` exists, ask:
   > "A previous run did not finish (sentinel present, change `<current_change>`). Resume / reset / abort?"
   - resume and reset both continue; entry detection (below) makes resume safe. reset only clears the sentinel first.
   - abort: exit without changes.
5. For every queue row with status `blocked-needs-human`, read `runs/<id>/escalation.md` and decide whether the human has acted:
   - kind `interview`: every `#### Human answer` block contains text (HTML comments do not count);
   - any other kind: the `## Human resolution` checkbox is ticked (`- [x]`).
   If so, set the row back to `in-progress` (it will resume). Otherwise leave it blocked. Never treat "no answer blocks" as resolved. If the requested `<change-id>` (or the first non-done row) is still blocked, stop and say: "Change `<id>` is still blocked — see `.openspec-worker/runs/<id>/escalation.md`."

## Sentinel

Write `.openspec-worker/run-context.json`:

```json
{
  "mode": "autonomous",
  "current_change": "<id>",
  "max_interview_rounds": 5,
  "iteration_caps": {
    "spec_author_validate": 3,
    "plan_validation": 3,
    "plan_split": 3,
    "review_fix": 3,
    "verify_fix": 3
  }
}
```

Update `current_change` as you advance. Remove the file when the run ends (success or escalation).

## Stale code-map refresh (once per run)

If `profile.code_map.enabled` and `.openspec-worker/code-map.json` exists:
```
Task(Sonnet, code-map-update, mode=stale)
```
This picks up code changed by hand (e.g. via `/opsx:apply`) since the map was last updated.

---

## Main loop

```
rows = queue rows with status in (queued, in-progress) [filtered to <change-id> if given]
for each row in order:
    id = row.change
    if not exists openspec/changes/<id>/:
        if exists openspec/changes/archive/*-<id>/: mark row done, log "already archived", continue
        ESCALATE("change folder missing: openspec/changes/<id>")
    set row.status = in-progress; sentinel.current_change = id
    ensure .openspec-worker/runs/<id>/ exists; open runs/<id>/run-log.md
    apply human answers if escalation.md present (see HUMAN ANSWERS)

    step = DETECT(id)
    run steps from `step` onward, in this order:
        INTERVIEW → SPEC-AUTHOR → PLAN → GROUP LOOP → VERIFY LOOP → ARCHIVE
    set row.status = done
    log "change <id> complete"

remove sentinel
report: "All queued changes done." (list of archived changes)
```

## DETECT(id)

Gather:
- `S = $OS status --change <id> --json` → `artifacts[]` (id, status)
- `A = $OS instructions apply --change <id> --json` → `progress`, `state`
- run folder files: `interview-brief.md`, `plan-notes.md`, `verify-result.md`, `spec-author-report.md`

Decide the first matching row:

| Condition | Step |
|---|---|
| `verify-result.md` status DONE and `progress.remaining == 0` | ARCHIVE |
| `tasks` done, `progress.total > 0`, `progress.remaining == 0` | VERIFY LOOP |
| `tasks` done and `plan-notes.md` exists | GROUP LOOP |
| `tasks` done, no `plan-notes.md` | PLAN (mode=adopt) |
| `interview-brief.md` exists, `proposal` done, `specs` done or skipped, no `tasks.md`, and `$OS validate <id> --strict --json` valid | PLAN (mode=new) |
| `interview-brief.md` exists | SPEC-AUTHOR |
| proposal is the only artifact present and `runs/<id>/brief.md` exists (seeded by bootstrap/enqueue) | INTERVIEW (mode=full) |
| anything else (human-authored change, partial artifacts) | INTERVIEW (mode=gap) |

Notes:
- `design` may be legitimately absent (OpenSpec treats it as optional), so it is never required for routing.
- Do not use `isPlanningComplete` for routing: it includes `tasks`, so it is false for every change that is ready to be planned.
- Log the decision: `| <time> | detect | — | status/apply JSON | step=<STEP> mode=<mode> | OK |`.

---

## INTERVIEW

```
rounds = number of rounds already in interview-history.json
while rounds < max_interview_rounds:
    Task(Opus, interview, change=<id>, mode=<full|gap>)
    if exists runs/<id>/interview-brief.md: break

    if exists runs/<id>/interview-questions.json:
        Task(Haiku, router, change=<id>)            → routed-questions.json
        for q in routed-questions.json.routed:          // independent: spawn in parallel
            Task(Opus, expert, question id = q.id)       // the expert reads its entry from routed-questions.json
                output: runs/<id>/expert-answers/<q.id>.json
        answers = merge expert-answers/*.json with a script (node/jq) — do not copy answer text by hand
        missing file for any q.id → ESCALATE("expert <q.id> produced no answer")
        log "expert <q.id> -> confidence=<level>" for each
        write runs/<id>/interview-answers.json = { round, answers }
        low = answers with confidence == "low"
        if low not empty:
            ESCALATE(kind=interview, questions=low)   // see escalation.md format
        append { round, questions, answers } to interview-history.json
        delete interview-questions.json, routed-questions.json, interview-answers.json, expert-answers/
    else:
        ESCALATE("interview round produced neither questions nor interview-brief.md")
    rounds++

if not exists interview-brief.md: ESCALATE("no interview-brief.md after <max> rounds")
if interview-brief.md has any Open Question tagged `deferrable: no`:
    ESCALATE(kind=interview, questions=those open questions)
```

Collect all expert answers of a round before escalating, so the human sees every low-confidence question at once.

## SPEC-AUTHOR

```
Task(Opus, spec-author, change=<id>)
    output: proposal.md, specs/**, design.md (if warranted) in the change; runs/<id>/spec-author-report.md
read spec-author-report.md
if status != VALID: ESCALATE("spec-author could not produce strict-valid artifacts: <issues>")
re-check yourself: $OS validate <id> --strict --json → items[0].valid must be true, else ESCALATE
```

## PLAN

```
Task(Opus, plan, change=<id>, mode=<new|adopt>)
    output: tasks.md (change), runs/<id>/plan-notes.md, runs/<id>/validation-report.md
read validation-report.md
BUDGET_OVERRUN → ESCALATE("token budget overrun: <reason>")
not APPROVED   → ESCALATE("plan validator failed: <issues>")
```

## GROUP LOOP

Groups are the `## N.` sections of `tasks.md` (listed in `plan-notes.md`). Start from the first group that has an unchecked task.

```
for each group N with unchecked tasks:
    iter = 0
    Task(Sonnet, implement, change=<id>, args="group-<N>")   → group-N-result.md
    if group-N-result.md status == GAP: ESCALATE("implementation gap in group N: <gap>")
    Task(Sonnet, code-map-update, result=group-N-result.md)
    loop:
        Task(Sonnet, review, change=<id>, args="group-<N>")  → review-N-report.md
        if status PASSED or no Must-fix: break
        if iter == review_fix cap: ESCALATE("group N review fix-loop hit cap")
        Task(Sonnet, implement, args='fix review-N "<must-fix summary>"') → fix-N-<iter>-result.md
        Task(Sonnet, code-map-update, result=fix-N-<iter>-result.md)
        iter++
    A = $OS instructions apply --json; every task of group N must be done, else ESCALATE("group N tasks left unchecked")
```

## VERIFY LOOP

```
iter = 0
loop:
    Task(Opus, verify, change=<id>)       → verify-result.md
    if status DONE: break
    if iter == verify_fix cap: ESCALATE("verify fix-loop hit cap with Must/Should issues")
    Task(Opus, implement, args='fix verify "<Must+Should summary>"') → fix-V-<iter>-result.md
    Task(Sonnet, code-map-update, result=fix-V-<iter>-result.md)
    iter++
```

## ARCHIVE

```
Task(Sonnet, archive, change=<id>)
    output: archived change, runs/<id>/archive-summary.md, runs/<id>/ moved to completed/<id>-<date>/
verify: openspec/changes/<id>/ no longer exists AND openspec/changes/archive/*-<id>/ exists
else ESCALATE("archive did not complete: see run-log")
```

After archive the run folder lives in `.openspec-worker/completed/<id>-<date>/`; write further log lines there.

---

## HUMAN ANSWERS

When resuming a change whose `runs/<id>/escalation.md` has kind `interview` and all `#### Human answer` blocks filled:
1. Build an answers list: for each question, `{ id, question, answer: <human text>, confidence: "human", rationale: "answered by a human after escalation" }`. Include the non-low expert answers of that round from `interview-answers.json` if it still exists.
2. Append the round to `interview-history.json` (with the questions from `interview-questions.json` if present, else the questions recorded in `escalation.md`).
3. Delete the round's transient files and rename `escalation.md` → `escalation-<n>-resolved.md`.
4. If the escalation was for `deferrable: no` open questions in `interview-brief.md`, also delete `interview-brief.md` so the next interview round folds the answers in.

For any other escalation kind, rename `escalation.md` → `escalation-<n>-resolved.md` and continue — DETECT finds the right step.

## ESCALATE procedure

```
queue row status = blocked-needs-human, Notes = "see runs/<id>/escalation.md"
write runs/<id>/escalation.md:
    # Escalation: <id>
    _Step: <step> · <ISO time>_
    _Kind: interview | spec-author | plan | implement | review | verify | archive | preflight_
    ## Reason
    <message>
    ## Questions for a human          (interview kind only; one block per question)
    ### <qid>: <question text>
    Expert attempt: <answer> (confidence: low — rationale: <rationale>)
    #### Human answer
    <!-- write your answer here, then re-run /openspec-worker:run -->
    ## What to do                     (other kinds)
    <concrete next action: which file to edit, or "continue manually with /opsx:apply <id>">
    ## Human resolution               (other kinds)
    - [ ] I fixed the cause above — resume this change on the next run
append "## Escalation" block with reason + last step + `ls` of runs/<id>/ to run-log.md
remove run-context.json
stop the entire run
tell the user: "Run halted on <id>: <reason>. See .openspec-worker/runs/<id>/escalation.md"
```

## Logging

Append one row per step to `runs/<id>/run-log.md` under a `## Step Log` header:
```
| 2026-10-15T14:02:11Z | implement group-1 | Sonnet | tasks.md, plan-notes.md | group-1-result.md | OK |
```
Also log each `$OS` call you make with the key JSON field (`valid`, `progress`, `archivedAs`).

## Task tool usage

Each Task call passes:
- `subagent_type`: `general-purpose` unless a dedicated agent type exists.
- `model`: as given above.
- `description`: short tag, e.g. "implement group 2".
- `prompt`: names the skill (e.g. "Run the `/openspec-worker:implement group-2` skill"), the working directory, the change id, that `.openspec-worker/run-context.json` is present so the skill runs autonomously, the `$OS` command value, and the exact output files it must produce.

After each Task, check the expected output file exists. Missing output → ESCALATE.

## Rules
- Never write OpenSpec artifacts or source code yourself.
- Never edit `profile.json`, `code-map.json`, `project-context.md`, or `openspec/config.yaml` directly.
- Never archive by calling `$OS archive` yourself — only the `archive` skill does, after its gates.
- Never proceed past a missing expected output.
- Never accept user input after preflight.
