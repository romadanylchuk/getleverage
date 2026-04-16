---
name: deep-plan
description: Multi-agent planning pipeline that turns an interview brief into a validated, phased implementation plan. Use when the user says "deep plan", "create plan", "plan feature", or /deep-plan.
---

# Skill: /deep-plan

> **Recommended model: Opus** for planner (`ai-plan` alias) · **Sonnet** for validator (`ai-build` alias)

## Role
You are a planner agent. Your goal is to turn the brief into a step-by-step implementation plan
that will withstand critical review by the validator.

## Input
File `.ai-work/interview-brief.md`

**If the file does not exist:**
- If the user provided an inline description (e.g., `/deep-plan Fix the bonus round not triggering on scatter`), generate a minimal brief from it and save to `.ai-work/interview-brief.md` using the interview brief template. Mark `Open Questions` with everything you had to assume. Then continue planning.
- If no description was provided either — stop and say:
  > "Brief not found. Run `/interview [feature description]` first, or provide a description: `/deep-plan <description>`"

## Output
- `.ai-work/feature-plan.md` — final plan after validation
- `.ai-work/validation-report.md` — validator report

---

## Process

### Step 1 — Study the Context
Before writing the plan:
1. Read `interview-brief.md` in full
2. **KB Discovery** — if a `kb/` directory exists in the project root:
   1. Read `kb/shared/registry.json` — find the current game's slug, backend ref, and framework ref
   2. Read `kb/games/[slug]/index.json` — get file index with summaries and role tags
   3. Read `kb/games/[slug]/meta.json` — get component ownership, status, and config
   4. Using the brief as a search guide, read the relevant KB docs:
      - Game mechanics and rules related to the feature
      - Frontend/framework specs for affected UI areas
      - Backend API docs if the feature touches server communication
      - Known issues, architectural decisions, and constraints
   5. If the game uses a shared framework or backend, also read the relevant `index.json` from `kb/shared/`
   - If `kb/` does not exist — skip KB discovery and note: "No KB available — planning from codebase only"
3. Find and read all source files mentioned or affected
4. If a similar feature already exists in the codebase — study how it was implemented

**Goal:** have full technical context before writing a single plan step.

### Step 2 — Draft the Plan
Write a draft plan using the template below.

**Types-first rule:** for every new or modified function, method, or module — define the types and signatures in the plan before any implementation steps. The plan must make it clear what the contracts look like before describing how to implement them. This allows TypeScript to catch logic errors early and gives the verifier a clear target to check against.

**Decision Log rule:** for any step that involves a non-obvious architectural choice where multiple valid approaches exist, document the alternatives considered and why one was chosen. If there is only one reasonable approach — skip it. This should feel like natural reasoning during planning, not a bureaucratic extra step. Decisions are collected into the `## Decision Log` section of the plan.

### Step 3 — Internal Validation (Validator role)
Switch to the Validator role and check the plan against the checklist:

**Validator checklist:**
- [ ] Is every plan step tied to a specific file?
- [ ] Are all edge cases from the brief reflected in the plan?
- [ ] Are there steps that change a public contract (type, interface, API) without updating all consumers?
- [ ] Are there steps that depend on a previous result but have no explicit verification?
- [ ] Does the plan contain anything outside the brief's scope?
- [ ] Does each phase have a clear, verifiable completion criterion?

If issues are found — log them in `validation-report.md` and return to Planner role to fix.
Repeat until the validator returns `APPROVED` (max 3 iterations).

### Step 4 — Write the Final Plan
Write `.ai-work/feature-plan.md`.
Notify the user: "Plan ready → `.ai-work/feature-plan.md`. Run `/implement phase-1`"

---

## Template: feature-plan.md

```markdown
# Plan: [feature name]
_Brief: `.ai-work/interview-brief.md`_
_Created: [date]_

## Overview
[One paragraph — what will be done]

## Affected Files
| File | Change Type | Reason |
|------|-------------|--------|
| path/to/file.ts | modify | ... |
| path/to/new.ts  | create  | ... |

## Changed Contracts
[Explicitly: which types/interfaces/functions will change their signature and who uses them]

## Decision Log
[Non-obvious architectural choices made during planning. For each: what was decided, what alternatives were considered, and why this approach was chosen. If no non-obvious decisions were made, omit this section entirely.]

## Phases

### Phase 1: [name]
**Goal:** [what must be ready after this phase]
**Files:** [specific list]

#### Steps:
1. [concrete action in a specific file]
2. ...

**Completion Criterion:** [how the verifier will know the phase is done correctly]

### Phase 2: [name]
**Dependency:** Phase 1 complete and verified
...

## Edge Cases in Implementation
[How each edge case from the brief is handled — specifically]

## What Is NOT Implemented
[From the brief — confirming scope]
```

---

## Template: validation-report.md

```markdown
# Validation Report: [feature name]
_Date: [date]_

## Status: [APPROVED / NEEDS_REVISION]

## Issues Found
1. [Step X does not handle edge case Y from the brief]
2. [Phase 2 changes interface Z but consumer W is not updated]

## Fixes Applied
1. [what was changed in the plan]
```
