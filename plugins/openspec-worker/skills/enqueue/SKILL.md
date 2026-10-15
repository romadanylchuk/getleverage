---
name: enqueue
description: Adds work to the openspec-worker queue — an existing OpenSpec change created by hand (/opsx:propose, openspec new change), a feature description, or a feature-brief file. Reports the step the worker will start from. Use when the user says "enqueue", "queue this change", "add change to worker", or /openspec-worker:enqueue <change-id | "description" | path/to/brief.md>.
---

# Skill: /openspec-worker:enqueue

> **Recommended model: Sonnet**

## Role
You add one item to `.openspec-worker/queue.md` and tell the user where the worker will pick it up. This is the "human → worker" handoff. You never run the pipeline.

`$OS` = `profile.openspec.command`.

## Preconditions
- `.openspec-worker/profile.json` exists, else: "Run `/openspec-worker:bootstrap` first."
- Create `.openspec-worker/queue.md` with the header table if it does not exist.
- If `.openspec-worker/run-context.json` exists, warn: "A run is active; the new row will be picked up when the run reaches it (or on the next run)." Continue.

## Input forms

### A) Existing change id
1. `$OS status --change <id> --json`. Error → list active changes (`$OS list --json`) and ask which one.
2. If already in the queue → show its row and stop (offer to reset a `blocked-needs-human` row to `queued`).
3. Summarize state for the user:
   - artifacts present (proposal / specs / design / tasks),
   - `$OS validate <id> --strict --json` result (valid + first issues),
   - `$OS instructions apply --change <id> --json` → task progress.
4. Predict the entry step using the DETECT table in `/openspec-worker:run` (origin `manual`, so a proposal-only change starts with a **gap-mode** interview).
5. Ask: "Queue `<id>` (entry: <step>)? Position: end / after <row> / first." Insert the row with origin `manual`, status `queued`, Notes `entry: <step>`.

### B) Feature description (free text)
1. Propose a kebab-case change id named for the change (e.g. `add-csv-export`); let the user confirm or edit.
2. `$OS new change <id> --description "<one line>" --json`.
3. Write `proposal.md` following `$OS instructions proposal --change <id> --json`: Why and What Changes from the description, Capabilities left as `- (to be decided by interview)`, Impact as far as known. Do not invent requirements.
4. Write `.openspec-worker/runs/<id>/brief.md` with the user's description verbatim under `# Feature Brief: <title>` / `## Goal`, and anything they said is out of scope under `## Out of Scope`.
5. Insert the queue row (origin `manual`, entry: interview full).

### C) Path to a feature-brief markdown file (architector format)
Same as bootstrap Step 5 for a single brief: copy to `.openspec-worker/feature-briefs/`, create the change, seed `proposal.md`, copy to `runs/<id>/brief.md`, insert row with origin `architector`.

## Output
The updated queue table and one line:
> "Queued `<id>` at position N — the worker will start with <step>. Run `/openspec-worker:run` (or `/openspec-worker:run <id>`)."

## Rules
- Never modify an existing change's specs, design or tasks.
- Never start the pipeline.
- Keep queue numbering contiguous after inserting.
