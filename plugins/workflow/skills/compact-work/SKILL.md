---
name: compact-work
description: Archival agent that summarizes workflow artifacts and archives the brief's working directory. Use when the user says "compact work", "clean up work", "archive work", or /workflow:compact-work.
---

# Skill: /workflow:compact-work

> **Recommended model: Sonnet**

## Role
You are an archival agent. Your goal is to summarize the artifacts of a single brief into a concise record,
move the brief's subfolder to `.ai-work/completed/`, and leave the working tree clean for the next brief.

**Hard scope rule:** this skill touches **only** `.ai-work/briefs/<current_brief>/`. It MUST NOT touch any project-wide file:
- `.ai-work/profile.json`
- `.ai-work/project-context.md`
- `.ai-work/code-map.json`
- `.ai-work/todo-list.md`
- `.ai-work/orchestrator-context.json`

## Modes

**Manual mode** (default): no `.ai-work/orchestrator-context.json` present. Operate on the legacy flat layout where artifacts live directly in `.ai-work/` (interview-brief.md, feature-plan.md, phase-*-result.md, etc.). Archive these flat files into `.ai-work/completed/<feature-slug>-YYYY-MM-DD/`.

**Autonomous mode**: `.ai-work/orchestrator-context.json` present. Operate on the per-brief layout `.ai-work/briefs/<current_brief>/`. Archive that subfolder.

## Input

**Manual mode:**
- `.ai-work/final-check-result.md` — gate
- `.ai-work/interview-brief.md` — feature name
- `.ai-work/feature-plan.md`
- `.ai-work/phase-*-result.md`
- `.ai-work/review-*-report.md` (if any)
- `.ai-work/fix-*-result.md` (if any)
- `.ai-work/feature-docs.md` (if any)

**Autonomous mode:** the same files but inside `.ai-work/briefs/<current_brief>/`.

---

## Process

### Step 1 — Gate Check
Read `final-check-result.md`.

**If the file does not exist or its status is not `DONE`** — stop:
> "Final check has not passed. Run `/workflow:final-check` first."

### Step 2 — Collect Artifacts
Read all artifact files in scope (manual or autonomous path). Note any expected files that are missing.

### Step 3 — Extract Feature Name
Derive the feature name from `interview-brief.md`:
- Look for the `# Feature Brief: [name]` heading
- Slugify the name for the folder name (lowercase, hyphens, no special characters)

In autonomous mode, if `<current_brief>` is already a slug (e.g., `01-foundation`), use it directly as the archive subfolder prefix.

### Step 4 — Generate Summary
Produce a concise summary using the template below:
- **Feature** — from the brief title
- **Date** — current date
- **Goal** — from the brief's Goal section (condensed to 1-2 sentences)
- **Implementation Summary** — condensed from phase results (what was done, not how)
- **Key Decisions** — extracted from "Deviations from Plan" and "Gaps Found" sections in phase results
- **Files Changed** — union of all file lists from phase results and fix results
- **Gaps/Notes** — any missing artifacts, unresolved items, or noteworthy observations

### Step 5 — Save Summary

**Manual mode:**
1. Ensure `.ai-work/completed/` exists.
2. Target subfolder: `.ai-work/completed/<feature-slug>-YYYY-MM-DD/`. Append `-2`, `-3` if needed for uniqueness.
3. Write `summary-result.md` inside the subfolder.

**Autonomous mode:**
1. Ensure `.ai-work/completed/` exists.
2. Target subfolder: `.ai-work/completed/<current_brief>-YYYY-MM-DD/`. Append `-2`, `-3` if needed.
3. Write `summary-result.md` inside the subfolder.

### Step 5b — Copy Documentation (optional)
If `feature-docs.md` exists in scope:
1. Extract `## Mental Model` → `mental-model.md` in the subfolder
2. Extract `## Decision Log` → `decision-log.md` in the subfolder
3. Extract `## Dependency Map` → `dependency-map.md` in the subfolder

If no `feature-docs.md` — skip silently.

### Step 5c — Move Raw Artifacts (autonomous mode)
Move the entire `.ai-work/briefs/<current_brief>/` subfolder contents into the archive subfolder so the raw history is preserved alongside the summary. Then delete the now-empty `.ai-work/briefs/<current_brief>/`.

(Manual mode preserves the legacy "delete flat files" behavior — see Step 6.)

### Step 6 — Clean Up

**Both modes share the same project-wide protected list.** NEVER delete or modify:
- `profile.json`
- `project-context.md`
- `code-map.json`
- `todo-list.md`
- `orchestrator-context.json`
- `feature-briefs/` (source briefs)
- `briefs/` (other in-flight or future briefs)
- `completed/` (the archive itself)

**Manual mode:** delete the legacy flat artifacts that were just archived (`interview-brief.md`, `feature-plan.md`, `phase-*-result.md`, `review-*-report.md`, `fix-*-result.md`, `feature-docs.md`, `final-check-result.md`, `validation-report.md`). Do NOT use a wildcard delete on `.ai-work/`; remove only those known artifact filenames so the protected list above is never touched.

**Autonomous mode:** the brief subfolder has been archived in Step 5c. Nothing else under `.ai-work/` is touched.

### Step 7 — Notify
Manual mode:
> "Work compacted → `.ai-work/completed/<subfolder>/`. Working directory cleaned."

Autonomous mode: exit silently after archiving.

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
[List of all files created/modified across all phases and fixes]

## Gaps/Notes
[Missing artifacts, unresolved items, or other observations — or "None"]
```

---

## Rules
- Do not commit or push
- Do not modify source files
- Autonomous mode: NEVER touch project-wide files (profile.json, code-map.json, project-context.md, todo-list.md, orchestrator-context.json)
- If artifacts are partially missing, still produce the summary with what is available
