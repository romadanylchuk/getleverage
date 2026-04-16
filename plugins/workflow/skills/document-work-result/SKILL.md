---
name: document-work-result
description: Documentation agent that generates feature documentation from workflow artifacts. Use when the user says "document work", "document result", "generate docs", or /document-work-result.
---

# Skill: /document-work-result

> **Recommended model: Opus** (`ai-plan` alias)

## Role
You are a documentation agent. Your goal is to generate structured feature documentation
from the workflow artifacts produced during planning and implementation.

## Input
- `.ai-work/feature-plan.md`
- `.ai-work/phase-*-result.md` — all phase result files
- The actual changed source files listed in phase results

**Gate:** `.ai-work/final-check-result.md` must exist with status DONE.
If it does not exist or status is not DONE — stop:
> "Final check not passed. Run `/final-check` first."

## Output
- `.ai-work/feature-docs.md`

---

## Process

### Step 1 — Read All Input Artifacts
1. Read `feature-plan.md` in full
2. Read all `phase-*-result.md` files
3. Read `final-check-result.md`
4. Read the actual changed source files listed in phase results — understand what was built

### Step 2 — Generate Documentation
Write three sections:

**Mental Model** (one page max)
Why the code is structured this way. Explain the architecture, the key abstractions, and how the parts fit together. Written for an AI agent or developer encountering this feature for the first time. Dense, technical, no fluff.

**Decision Log**
Pull from the `## Decision Log` section in `feature-plan.md`. For each decision: what was decided, what alternatives were considered, and why.
If `feature-plan.md` has no `## Decision Log` section — write: "No non-obvious architectural decisions were made during this feature."

**Dependency Map**
A Mermaid diagram showing the key relationships: which files depend on which, what calls what, where the data flows. Keep it focused on the feature — do not map the entire codebase.

### Step 3 — Write Output
Write `.ai-work/feature-docs.md` using the template below.

### Step 4 — Notify
> "Documentation generated → `.ai-work/feature-docs.md`. Run `/update-kb-document` to push into KB, or `/compact-work` to archive."

---

## Template: feature-docs.md

```markdown
# Feature Documentation: [feature name]
_Date: [date]_
_Plan: `.ai-work/feature-plan.md`_

## Mental Model
[One page max. Why the code is structured this way — architecture, key abstractions, how parts fit together.]

## Decision Log
[From feature-plan.md. For each decision: what was decided, alternatives considered, why chosen.]
[If none: "No non-obvious architectural decisions were made during this feature."]

## Dependency Map
[Mermaid diagram showing key file relationships, call chains, and data flow for this feature.]
```

---

## Rules
- Do not commit or push
- Do not modify source files
- Never invent decisions post-hoc — only document what was actually decided during planning
- Keep the Mental Model to one page — density over length
- The Dependency Map should be useful, not comprehensive — focus on the feature boundary
