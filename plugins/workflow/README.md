# workflow

AI development workflow — structured pipeline from feature interview to implementation, review, and archival.

## Flow

```
/interview [feature description]
      ↓ creates: .ai-work/interview-brief.md

/deep-plan
      ↓ reads:   interview-brief.md
      ↓ creates: feature-plan.md + validation-report.md

/implement phase-1        ← new chat, /clear before running
      ↓ reads:   feature-plan.md
      ↓ creates: phase-1-result.md [VERIFIED]

/implement phase-2        ← new chat, /clear before running
      ↓ reads:   feature-plan.md + phase-1-result.md
      ↓ creates: phase-2-result.md [VERIFIED]

/review phase-N           ← optional, after each /implement
      ↓ reads:   phase-N-result.md + changed source files
      ↓ creates: review-N-report.md

/review all               ← optional, before /final-check
      ↓ reads:   all phase-*-result.md + changed source files
      ↓ creates: review-all-report.md

/final-check              ← new chat
      ↓ reads:   interview-brief.md + all phase-*-result.md
      ↓ creates: final-check-result.md

/document-work-result     ← optional, same chat or new chat
      ↓ reads:   feature-plan.md + phase-*-result.md + source files
      ↓ creates: feature-docs.md

/update-kb-document       ← optional, after /document-work-result
      ↓ reads:   feature-docs.md + KB structure
      ↓ creates: KB entry .md + updates index.json

/compact-work             ← new chat
      ↓ reads:   all .ai-work/ artifacts
      ↓ creates: .ai-work/completed/[slug]-YYYY-MM-DD/
```

## Skills

| Skill | Description |
|-------|-------------|
| `/interview` | Analyst agent — interviews the user and produces a structured feature brief |
| `/deep-plan` | Planner agent — turns a brief into a validated, phased implementation plan |
| `/implement` | Developer agent — implements one phase with built-in verification |
| `/review` | Reviewer agent — evaluates code quality after implementation |
| `/final-check` | Auditor agent — verifies the full feature against the original brief |
| `/document-work-result` | Documentation agent — generates feature docs from workflow artifacts |
| `/update-kb-document` | KB integration agent — pushes feature docs into the knowledge base |
| `/compact-work` | Archival agent — summarizes artifacts and cleans up `.ai-work/` |

## When to Clear Context

| Transition | Action |
|------------|--------|
| interview → deep-plan | /clear or new chat |
| deep-plan → implement phase-1 | **mandatory** new chat |
| phase-N → review | same chat or new chat — both work |
| review → phase-N+1 | **mandatory** new chat |
| last phase → final-check | new chat |
| final-check → document-work-result | same chat or new chat |
| document-work-result → update-kb-document | same chat |
| update-kb-document → compact-work | new chat |

**Rule:** every `/implement` starts with a clean context.

## When to Use Which Skill

| Situation | Skill |
|-----------|-------|
| Simple bug or small change | go straight to `/deep-plan` |
| New feature with unknown edge cases | `/interview` → `/deep-plan` |
| Feature touching multiple modules | `/interview` → `/deep-plan` |
| Refactoring | `/deep-plan` (no interview) |
| Fix after `/final-check` issues | `/implement fix "description"` |
| Review code quality after a phase | `/review phase-N` |
| Review entire feature before final-check | `/review all` |
| Feature introduces new patterns or touches multiple modules | `/document-work-result` |
| Feature adds something other AI sessions need to know | `/update-kb-document` |
| Archiving completed work | `/compact-work` |
