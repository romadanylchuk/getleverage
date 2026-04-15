# Architector

A multi-session architecture exploration workflow that turns raw ideas into
implementation-ready feature briefs for the development workflow.

## Installation

**As a plugin (recommended):**
```bash
# Clone the repo
git clone https://github.com/RDanylchuk/Architector.git

# Use it with Claude Code
claude --plugin-dir /path/to/Architector
```

**For development:**
```bash
cd Architector
claude --plugin-dir .
```

Once installed, all skills are available as `/architector:init`, `/architector:explore`, etc.

## Flow

```
/architector:init [project description]
      ↓ creates: .ai-arch/project-context.md
                 .ai-arch/index.json
                 .ai-arch/ideas/[slug].md  (one per idea node)

/architector:explore                 ← navigate and deepen any node
/architector:map                     ← visualise connections (use anytime)
/architector:decide [node]           ← lock in a decision with rationale
/architector:status                  ← where are we, what's blocking

      ↓ repeat until all blocking nodes reach `ready`

/architector:finalize
      ↓ creates: .ai-arch/feature-briefs/NN-[slug].md
                 .ai-arch/todo-list.md

      ↓ each stage enters the implementation workflow:
        /interview or /deep-plan → /implement → /final-check
```

## When to Use Which Skill

| Situation | Skill |
|-----------|-------|
| Starting a new project from scratch | `/architector:init` |
| Want to see all nodes and their status | `/architector:explore` (shows dashboard) |
| Want to go deeper on a specific idea | `/architector:explore [node]` |
| Want to understand how ideas relate | `/architector:map` |
| Two ideas might be the same thing | `/architector:map [a] [b]` |
| Ready to commit to a direction | `/architector:decide [node]` |
| Want a progress snapshot | `/architector:status` |
| All blocking nodes are ready | `/architector:finalize` |

## Idea Node Maturity

```
raw-idea → explored → decided → ready
```

| Maturity | Symbol | Meaning |
|----------|--------|---------|
| raw-idea | ◻ | Named and described, nothing more |
| explored | ◽ | Discussed in depth, tradeoffs surfaced |
| decided  | ◈ | Approach chosen, rationale documented |
| ready    | ✦ | Fully specified, can enter /deep-plan workflow |

Maturity is advanced by:
- `raw-idea → explored` : `/architector:explore`
- `explored → decided`  : `/architector:decide`
- `decided → ready`     : `/architector:decide` (when all open questions resolved)

## Node Priority

| Priority | Meaning |
|----------|---------|
| `blocking` | Must reach `ready` before `/architector:finalize` can run |
| `core` | Central to the product, should be decided before finalize |
| `extension` | Valuable but not required for first implementation pass |
| `deferred` | Consciously set aside — will not appear in todo list |

**Gate rule:** `/architector:finalize` requires all `blocking` nodes to be at `ready`.
Non-blocking nodes that aren't ready are flagged but do not block finalization.

## .ai-arch/ Structure

```
.ai-arch/
  project-context.md          ← shared context (product type, constraints, out of scope)
  index.json                  ← all nodes, connections, session history
  ideas/
    tech-stack.md             ← one file per idea node
    data-model.md
    canvas-ui.md
    ...
    [slug].archived.md        ← merged/split nodes (kept for history)
  feature-briefs/
    01-foundation.md          ← output of /architector:finalize
    02-auth.md
    03-canvas.md
    ...
  todo-list.md                ← master implementation list
```

**Add `.ai-arch/` to `.gitignore`** if you don't want architecture exploration in version history.
Or commit it — the decision history is valuable.

## Relationship to the Implementation Workflow

Architect flow and the implementation workflow are separate tracks.

```
Architect flow (.ai-arch/)          Implementation workflow (.ai-work/)
─────────────────────────           ──────────────────────────────────
/architector:init                   /interview
/architector:explore     ──────→    /deep-plan
/architector:map      feature-brief /implement phase-N
/architector:decide                 /review
/architector:status                 /final-check
/architector:finalize               /document-work-result
                                    /update-kb-document
                                    /compact-work
```

Feature briefs from `/architector:finalize` are the handoff point.
Each brief is the starting input for one run of the implementation workflow.

## Tips

- **Run `/architector:map` early and often.** Even with raw-idea nodes, it surfaces hidden dependencies and merge candidates before you go deep on the wrong thing.
- **Don't rush to `/architector:decide`.** A premature decision on a poorly explored node creates false certainty. Explore first.
- **Blocking nodes first.** Tech stack, core data model, platform choice — these unblock everything else. Run `/architector:status` to see the dependency chain.
- **Use deferred honestly.** If an idea won't affect the first implementation pass, mark it deferred. It keeps the map clean and finalization reachable.
- **Feature briefs don't need to be complete.** If a brief has open technical questions, that's fine — `/interview` will resolve them. The brief just needs enough context to start the conversation.
- **The todo list is a living document.** Update the status column as stages complete. It becomes your project log.

## Development

To work on the skills themselves:

```bash
cd Architector
claude --plugin-dir .
```

Each skill is self-contained in `skills/<name>/SKILL.md`. The plugin manifest is at `.claude-plugin/plugin.json`.
