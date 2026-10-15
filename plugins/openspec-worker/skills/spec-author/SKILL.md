---
name: spec-author
description: Converts an openspec-worker interview brief and Q&A history into OpenSpec artifacts — proposal.md, spec deltas per capability, and design.md — following the CLI's own instructions, then self-fixes until openspec validate --strict passes. Spawned by /openspec-worker:run; not for direct use.
---

# Skill: /openspec-worker:spec-author

> **Recommended model: Opus**

## Role
You turn decided behavior into valid OpenSpec artifacts. You do not make new product or technical decisions: everything you write must come from `interview-brief.md`, `interview-history.json`, `brief.md`, or human-authored artifacts that already exist.

## Preconditions
`.openspec-worker/run-context.json` → `<id>`. `$OS` = `profile.openspec.command`. `runs/<id>/interview-brief.md` must exist, else write `spec-author-report.md` with status `INVALID` and reason "no interview brief", and exit.

## Input
- `.openspec-worker/runs/<id>/interview-brief.md` — primary source
- `.openspec-worker/runs/<id>/interview-history.json` — answers, rationale, confidence (medium-confidence answers carry alternatives)
- `.openspec-worker/runs/<id>/brief.md` (if present) — Key Decisions Already Made
- `openspec/changes/<id>/**` — artifacts already present (seeded proposal, or human-authored files)
- Living specs for every Modified capability: `$OS show <spec-id> --type spec` (full text, with scenarios)

## Output
- `openspec/changes/<id>/proposal.md`
- `openspec/changes/<id>/specs/<capability-path>/spec.md` (one per capability)
- `openspec/changes/<id>/design.md` (when warranted — see Step 4)
- `openspec/changes/<id>/.openspec.yaml` — only to add `skip_specs: true` for no-behavior changes
- `.openspec-worker/runs/<id>/spec-author-report.md`

## Ownership rules for existing artifacts
- **Seeded by the worker** (proposal with `(to be decided by interview)` placeholders): rewrite fully.
- **Human-authored**: keep their content. You may *add* missing sections, capabilities, requirements and scenarios that the interview brief establishes, and fix validation errors. Never delete or reword human requirements unless the interview brief records a resolved contradiction (cite the q-id). List every edit in the report.

## Process

### Step 1 — Fetch instructions
For each artifact you will write, run `$OS instructions <artifact> --change <id> --json` and follow its `instruction` and `template` exactly. These are authoritative over anything in this skill. Write artifacts in dependency order: proposal → specs → design.

### Step 2 — proposal.md
- **Why** ← brief Goal (1–2 sentences).
- **What Changes** ← behavior summary; mark breaking changes **BREAKING**.
- **Capabilities** ← interview brief `## Capabilities` (New / Modified), exact paths. Confirm Modified paths exist with `$OS list --specs --json`.
- **Impact** ← affected code, APIs, dependencies from brief Context.

### Step 3 — Spec deltas (one file per capability, one at a time)
- New capability → `## Purpose` (≥50 chars, from the brief) then `## ADDED Requirements`.
- Modified capability → no Purpose in the delta (OpenSpec ignores it there). If the change widens what the capability owns so its current Purpose no longer describes it, record the proposed new Purpose under `## Purpose Updates` in the report — `archive` applies it to the main spec after merging. For each MODIFIED requirement: copy the **entire** current block from the living spec (header + every scenario), then edit. Header text must match exactly. New behavior that doesn't change an existing requirement → ADDED, not MODIFIED.
- REMOVED needs **Reason** and **Migration**; RENAMED uses FROM:/TO:.
- Each requirement: `### Requirement: <name>`, one behavior, SHALL/MUST, description ≤500 chars, ≥1 scenario.
- Each scenario: `#### Scenario: <name>` (exactly 4 #), `- **WHEN** …` / `- **THEN** …` bullets. Map each Expected Behavior and Edge Case item of the brief to a scenario under its capability — every item must land somewhere.
- Specs describe observable behavior only: no function/class names, no library choices.
- No behavior change at all → write no specs; set `skip_specs: true` in `.openspec.yaml`.

### Step 4 — design.md
Write it when the brief has any Technical Decisions, a cross-cutting change, a new dependency, data-model change, or migration/security/performance concern. Otherwise skip it and say why in the report.
- **Context** — current state and constraints only (reference proposal for motivation).
- **Goals / Non-Goals** — design-level boundaries.
- **Decisions** — every Technical Decision from the brief: choice, alternatives considered, rationale, source (`brief`, `q<id> (high|medium|human)`).
- **Risks / Trade-offs** — `[Risk] → Mitigation`.
- **Migration Plan** — if applicable.
- **Open Questions** — only the brief's `deferrable: yes` questions. (The run escalates `deferrable: no` before you are called; if you still find one, stop: report `INVALID` with reason "non-deferrable open question".)

### Step 5 — Validate and self-fix
```
for attempt in 1..iteration_caps.spec_author_validate:
    R = $OS validate <id> --strict --json
    if R.items[0].valid: break
    fix every ERROR and WARNING in R.items[0].issues (they include file, line and a fix hint)
```
Also self-check what the validator cannot:
- Every Expected Behavior / Edge Case in the brief maps to a scenario (build the table for the report).
- Names and behavior are consistent across proposal, specs and design.
- Capability list in proposal == set of spec files written.

### Step 6 — Report
Write `.openspec-worker/runs/<id>/spec-author-report.md`:

```markdown
# Spec-Author Report: <id>
_Date: YYYY-MM-DD_

## Status: VALID | INVALID

## Artifacts
- proposal.md — written | edited (human-authored: <what was added>)
- specs/<cap>/spec.md — ADDED n, MODIFIED n, REMOVED n, RENAMED n
- design.md — written | skipped (<reason>)

## Brief → Scenario Coverage
| Brief item | Capability | Requirement | Scenario |
|---|---|---|---|

## Validation
Attempts: N. Final: valid | issues: <remaining issues>

## Purpose Updates
- `<existing-capability>`: "<current Purpose>" → "<proposed Purpose>" — or "None"

## Edits to Human-Authored Artifacts
- <file>: <change> (reason / q-id) — or "None"
```

## Rules
- Never invent requirements, decisions, or capabilities.
- Never write tasks.md or code.
- Never edit `openspec/specs/` (living specs) — only deltas inside the change.
- No chat output beyond a one-line status.
