# workflow

Tech-agnostic AI development workflow — structured pipeline from feature interview through implementation, review, and archival. Works as a hand-driven manual workflow or as the engine that `orchestrator-team-lead` drives autonomously.

## Modes

Every skill in this plugin operates in two modes, chosen automatically:

- **Manual** (default): conversational, prompts the user, behaves as a hand-driven workflow.
- **Autonomous**: triggered when `.ai-work/orchestrator-context.json` is present. Skills read inputs from `.ai-work/briefs/<current_brief>/`, write outputs there, and exit silently. The orchestrator drives the pipeline.

## Project profile

This workflow is tech-agnostic. All language-specific and tooling-specific behavior is driven by `.ai-work/profile.json`:

```json
{
  "language": "typescript",
  "type_system": "strict",
  "contracts_first": true,
  "build":  { "command": "pnpm build" },
  "lint":   { "command": "pnpm lint" } | null,
  "test":   { "command": "pnpm test" } | null,
  "patterns": {
    "error_handling": "Result types",
    "naming": "camelCase functions, PascalCase types"
  },
  "code_map": { "enabled": true, "exclude": ["node_modules", "dist"] },
  "phase_token_budget": 130000,
  "phase_token_warn_at": 90000
}
```

If a tool is absent (no linter, no tests), set the field to `null` and the corresponding checks are skipped. Linter and tests are part of the project's architecture: if the project doesn't have them, the workflow doesn't pretend to run them.

The profile is created by `/orchestrator:bootstrap` (from the `orchestrator-team-lead` plugin), or hand-written for manual use.

## Manual flow

```
/workflow:interview [feature description]
      ↓ creates: .ai-work/interview-brief.md

/workflow:deep-plan
      ↓ reads:   interview-brief.md + profile.json + code-map.json
      ↓ creates: feature-plan.md (with per-phase token estimates) + validation-report.md

/workflow:implement phase-1        ← new chat, /clear before running
      ↓ reads:   feature-plan.md + profile.json
      ↓ creates: phase-1-result.md [VERIFIED]

/workflow:implement phase-2        ← new chat, /clear before running
      ↓ reads:   feature-plan.md + phase-1-result.md
      ↓ creates: phase-2-result.md [VERIFIED]

/workflow:review phase-N           ← optional, after each /workflow:implement
      ↓ creates: review-N-report.md

/workflow:review all               ← optional, before /workflow:final-check
      ↓ creates: review-all-report.md

/workflow:final-check              ← new chat
      ↓ reads:   interview-brief.md + all phase-*-result.md
      ↓ creates: final-check-result.md

/workflow:document-work-result     ← optional
      ↓ creates: feature-docs.md

/workflow:compact-work             ← new chat
      ↓ archives .ai-work/ → .ai-work/completed/[slug]-YYYY-MM-DD/
```

## Skills

| Skill | Description |
|-------|-------------|
| `/workflow:interview` | Analyst agent — interviews the user and produces a structured feature brief |
| `/workflow:deep-plan` | Planner agent — turns a brief into a validated, phased implementation plan with token-budget-checked phases |
| `/workflow:implement` | Developer agent — implements one phase with built-in verification driven by `profile.json` |
| `/workflow:review` | Reviewer agent — evaluates code quality after implementation |
| `/workflow:final-check` | Auditor agent — verifies the full feature against the original brief |
| `/workflow:document-work-result` | Documentation agent — generates feature docs from workflow artifacts |
| `/workflow:compact-work` | Archival agent — archives the brief's artifacts into `.ai-work/completed/` |

## When to Clear Context (manual mode)

| Transition | Action |
|------------|--------|
| interview → deep-plan | /clear or new chat |
| deep-plan → implement phase-1 | **mandatory** new chat |
| phase-N → review | same chat or new chat — both work |
| review → phase-N+1 | **mandatory** new chat |
| last phase → final-check | new chat |
| final-check → document-work-result | same chat or new chat |
| document-work-result → compact-work | new chat |

**Rule:** every `/workflow:implement` starts with a clean context.

## When to Use Which Skill

| Situation | Skill |
|-----------|-------|
| Simple bug or small change | go straight to `/workflow:deep-plan` |
| New feature with unknown edge cases | `/workflow:interview` → `/workflow:deep-plan` |
| Feature touching multiple modules | `/workflow:interview` → `/workflow:deep-plan` |
| Refactoring | `/workflow:deep-plan` (no interview) |
| Fix after `/workflow:final-check` issues | `/workflow:implement fix "description"` |
| Review code quality after a phase | `/workflow:review phase-N` |
| Review entire feature before final-check | `/workflow:review all` |
| Feature touches multiple modules or new patterns | `/workflow:document-work-result` |
| Archiving completed work | `/workflow:compact-work` |

## Autonomous mode

Use `orchestrator-team-lead` to drive this workflow over a queue of feature briefs. The orchestrator drops `.ai-work/orchestrator-context.json` and these skills switch into file-only mode. See the orchestrator plugin's README for details.

## What changed in v2.0

- All TypeScript/ESLint specifics removed; everything is driven by `profile.json`.
- "Types-first" generalized to "contracts-first" (gated by `profile.contracts_first`).
- KB references removed entirely; replaced by `profile.json`, `project-context.md`, and `code-map.json`.
- Every skill gained autonomous mode for orchestrator integration.
- `/workflow:deep-plan` gained a per-phase token budget check with automatic split.
- `/workflow:compact-work` scope strictly limited to per-brief archives in autonomous mode.
- `/update-kb-document` removed.
