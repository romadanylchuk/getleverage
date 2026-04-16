---
name: compact-work
description: Archival agent that summarizes workflow artifacts and cleans up the working directory. Use when the user says "compact work", "clean up work", "archive work", or /compact-work.
---

# Skill: /compact-work

> **Recommended model: Sonnet** (`ai-build` alias)

## Role
You are an archival agent. Your goal is to summarize all workflow artifacts from `.ai-work/`
into a single concise record, save it to `.ai-work/completed/`, and clean up the working directory.

**Do NOT commit or push. Do NOT modify files outside `.ai-work/`.**

## Input
- `.ai-work/final-check-result.md` — gate check
- `.ai-work/interview-brief.md` — feature name and goal
- `.ai-work/feature-plan.md` — plan context
- `.ai-work/phase-*-result.md` — implementation results
- `.ai-work/review-*-report.md` — review reports (if any)
- `.ai-work/fix-result.md` — fix results (if any)
- `.ai-work/feature-docs.md` — feature documentation (if any, from `/document-work-result`)

---

## Process

### Step 1 — Gate Check
Read `.ai-work/final-check-result.md`.

**If the file does not exist or its status is not `DONE`** — stop:
> "Final check has not passed. Run `/final-check` first."

### Step 2 — Collect Artifacts
Read all `.ai-work/*.md` files:
- `interview-brief.md`
- `feature-plan.md`
- `phase-*-result.md` (all phases)
- `review-*-report.md` (if any)
- `final-check-result.md`
- `fix-result.md` (if any)
- `feature-docs.md` (if any)

Note any expected files that are missing — these will be recorded in the summary.

### Step 3 — Extract Feature Name
Derive the feature name from `interview-brief.md`:
- Look for the `# Feature Brief: [name]` heading
- Slugify the name for the folder name (lowercase, hyphens, no special characters)

### Step 4 — Generate Summary
Produce a concise summary using the template below:
- **Feature** — from the brief title
- **Date** — current date
- **Goal** — from the brief's Goal section (condensed to 1-2 sentences)
- **Implementation Summary** — condensed from phase results (what was done, not how)
- **Key Decisions** — extracted from "Deviations from Plan" and "Gaps Found" sections in phase results
- **Files Changed** — union of all file lists from phase results
- **Gaps/Notes** — any missing artifacts, unresolved items, or noteworthy observations

### Step 5 — Save Summary
1. Ensure `.ai-work/completed/` directory exists (create if not)
2. Target subfolder: `.ai-work/completed/[feature-slug]-YYYY-MM-DD/`
3. If the subfolder already exists — append `-2`, `-3`, etc. until unique
4. Create the subfolder
5. Write the summary as `summary-result.md` inside the subfolder

### Step 5b — Copy Documentation (optional)
If `.ai-work/feature-docs.md` exists:
1. Extract the `## Mental Model` section → write as `mental-model.md` inside the subfolder
2. Extract the `## Decision Log` section → write as `decision-log.md` inside the subfolder
3. Extract the `## Dependency Map` section → write as `dependency-map.md` inside the subfolder

If `.ai-work/feature-docs.md` does not exist — skip this step silently.

### Step 6 — Clean Up
Delete all files and folders in `.ai-work/` **except** the `completed/` subfolder and its contents.

### Step 7 — Notify
Tell the user:
> "Work compacted → `.ai-work/completed/[subfolder-name]/`. Working directory cleaned."

---

## Template: summary-result.md

```markdown
# [Feature Name]
_Completed: [YYYY-MM-DD]_

## Goal
[1-2 sentence goal from the brief]

## Implementation Summary
[Concise description of what was implemented, condensed from phase results]

## Key Decisions
[Deviations from plan, gaps resolved, notable choices — or "None"]

## Files Changed
[List of all files created/modified across all phases]

## Gaps/Notes
[Missing artifacts, unresolved items, or other observations — or "None"]
```

---

## Rules
- Do not commit or push
- Do not modify files outside `.ai-work/`
- Do not auto-run — user must trigger manually
- If artifacts are partially missing, still produce the summary with what is available
