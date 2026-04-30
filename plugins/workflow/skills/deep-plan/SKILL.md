---
name: deep-plan
description: Multi-agent planning pipeline that turns an interview brief into a validated, phased implementation plan. Use when the user says "deep plan", "create plan", "plan feature", or /workflow:deep-plan.
---

# Skill: /workflow:deep-plan

> **Recommended model: Opus** for planner · **Sonnet** for validator

## Role
You are a planner agent. Your goal is to turn the brief into a step-by-step implementation plan
that will withstand critical review by the validator and fit the project's token budget.

## Modes

**Manual mode** (default): no `.ai-work/orchestrator-context.json` present. Behave as today.

**Autonomous mode**: `.ai-work/orchestrator-context.json` exists. Read inputs from `.ai-work/briefs/<current_brief>/`, write outputs there, exit after writing without prompting the user.

## Input

> **Path notation:** `.ai-work/[briefs/<current_brief>/]<file>` is shorthand for two paths. Manual mode resolves to `.ai-work/<file>`. Autonomous mode resolves to `.ai-work/briefs/<current_brief>/<file>`.

- `.ai-work/[briefs/<current_brief>/]interview-brief.md`
- `.ai-work/profile.json` — project profile (drives all language/tooling decisions)
- `.ai-work/project-context.md` (optional)
- `.ai-work/code-map.json` (optional but preferred — narrows file discovery)

**If `interview-brief.md` does not exist:**
- Manual mode: if the user provided an inline description, generate a minimal brief from it; otherwise stop and tell them to run `/workflow:interview` first.
- Autonomous mode: stop with an error written to the orchestrator log. The orchestrator should not have invoked you without a brief.

**If `profile.json` does not exist:**
- Manual mode: ask the user to run `/orchestrator:bootstrap` first, OR continue with conservative defaults (typed language, build/lint/test all assumed) and warn.
- Autonomous mode: stop with an error.

## Output
- `feature-plan.md` — final plan after validation and budget check
- `validation-report.md` — validator report

---

## Process

### Step 1 — Study the Context
Before writing the plan:

1. Read `interview-brief.md` in full.
2. Read `profile.json` — note language, type system, build/lint/test commands, patterns. Everything tech-specific in the rest of this skill is driven by this file.
3. Read `project-context.md` if it exists.
4. **Code map discovery** — if `code-map.json` exists, use it as the navigation index:
   - Find files whose `summary` or `role` matches the brief's affected areas.
   - Follow `depends_on` edges to see what else may be affected.
   - Use this to narrow which files to read in full, not as a substitute for reading them.
5. Read all source files mentioned or affected — **read the actual files** for any file you will modify or whose contract you depend on. The map is for navigation, not for content.
6. If a similar feature already exists in the codebase — study how it was implemented.

**Goal:** have full technical context before writing a single plan step.

### Step 2 — Draft the Plan
Write a draft plan using the template below.

**Contracts-first rule** (gated by `profile.contracts_first`): for every new or modified function, method, or module — define the contracts (signatures, schemas, types, JSDoc, whatever the project uses) in the plan before any implementation steps. The plan must make the contracts clear before describing how to implement them. This gives the verifier a clear target to check against. If `profile.contracts_first` is false, skip this rule.

**Decision Log rule:** for any step involving a non-obvious architectural choice where multiple valid approaches exist, document the alternatives considered and why one was chosen. If only one reasonable approach exists, skip it. Decisions are collected into the `## Decision Log` section of the plan.

### Step 3 — Internal Validation (Validator role)
Switch to the Validator role and check the plan against the checklist.

**Validator checklist:**
- [ ] Is every plan step tied to a specific file?
- [ ] Are all edge cases from the brief reflected in the plan?
- [ ] Are there steps that change a public contract (type, interface, API, schema) without updating all consumers?
- [ ] Are there steps that depend on a previous result but have no explicit verification?
- [ ] Does the plan contain anything outside the brief's scope?
- [ ] Does each phase have a clear, verifiable completion criterion?
- [ ] Does the plan respect `profile.patterns` (error handling style, naming conventions)?
- [ ] Does each phase fit within `profile.phase_token_budget`? (See Token Budget Check below)

If issues are found — log them in `validation-report.md` and return to Planner role to fix.
Repeat until the validator returns `APPROVED` (max 3 iterations).

### Step 4 — Token Budget Check
After validator returns APPROVED, run a budget check on every phase.

**Estimate per phase:**
```
phase_estimate =
    8K   (skill + profile + sentinel baseline)
  + size(feature-plan.md)
  + size(prior phase-result.md files accumulated up to this phase)
  + size(code-map.json)
  + sum of file sizes for "Affected Files" listed in this phase
  + sum of file sizes for files in those files' `depends_on` (from code-map)
  + 30% headroom (for similar-impl reads, verifier round, output, corrections)
```

Use `chars / 4` as a rough token-per-char ratio; precision is not required.

**Decision logic:**
- `estimate ≤ profile.phase_token_warn_at`: phase OK.
- `warn_at < estimate ≤ profile.phase_token_budget`: warn in plan output, do not split.
- `estimate > budget`: split required.

**Split strategies, in order:**
1. **Natural split** — phase already does N logically distinct things; split along that seam (e.g., "phase 3a — schema migration", "phase 3b — API handlers").
2. **File-group split** — group files by dependency clusters; files sharing a contract change stay together; independent files become a follow-up phase.

After splitting, re-run validator. Cap at 3 split iterations.

**Single-file budget overrun:** if a single file in a phase exceeds the budget, splitting cannot help. Write `.ai-work/[briefs/<current_brief>/]budget-overrun.md` describing the file and the gap, set the validator status to `BUDGET_OVERRUN`, and stop. The user (or orchestrator) must refactor the file or raise the budget.

### Step 5 — Write the Final Plan
Write the final plan file. Each phase section must include `**Estimated context:** ~XXK tokens`.

**Manual mode notify:** "Plan ready → `.ai-work/feature-plan.md`. Run `/workflow:implement phase-1`"
**Autonomous mode:** exit silently after writing.

---

## Template: feature-plan.md

```markdown
# Plan: [feature name]
_Brief: `interview-brief.md`_
_Created: [date]_

## Overview
[One paragraph — what will be done]

## Affected Files
| File | Change Type | Reason |
|------|-------------|--------|
| path/to/file | modify | ... |
| path/to/new  | create  | ... |

## Changed Contracts
[Explicitly: which contracts (types, interfaces, schemas, function signatures) will change and who uses them]

## Decision Log
[Non-obvious architectural choices made during planning. For each: what was decided, alternatives considered, why this approach was chosen. Omit section entirely if no non-obvious decisions.]

## Phases

### Phase 1: [name]
**Goal:** [what must be ready after this phase]
**Files:** [specific list]
**Estimated context:** ~XXK tokens

#### Steps:
1. [concrete action in a specific file]
2. ...

**Completion Criterion:** [how the verifier will know the phase is done correctly]

### Phase 2: [name]
**Dependency:** Phase 1 complete and verified
**Estimated context:** ~XXK tokens
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

## Status: [APPROVED / NEEDS_REVISION / BUDGET_OVERRUN]

## Issues Found
1. [Step X does not handle edge case Y from the brief]
2. [Phase 2 changes contract Z but consumer W is not updated]

## Budget Check
| Phase | Estimate | Budget | Status |
|-------|----------|--------|--------|
| 1 | 65K | 130K | OK |
| 2 | 145K | 130K | SPLIT (became 2a, 2b) |

## Fixes Applied
1. [what was changed in the plan]
```

---

## Rules
- Read actual files for any contract you depend on; never substitute the code-map for source content
- Never plan changes to files not in `Affected Files`
- Phases must respect the token budget — split when needed
- Profile-driven: language/tooling decisions come from `profile.json`, not from this skill's text
