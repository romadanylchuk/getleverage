# Architect Flow

A multi-session architecture exploration workflow that turns raw ideas into
implementation-ready feature briefs for the development workflow.

## Flow

```
/arch-init [project description]
      ↓ creates: .ai-arch/project-context.md
                 .ai-arch/index.json
                 .ai-arch/ideas/[slug].md  (one per idea node)

/arch-explore                    ← navigate and deepen any node
/arch-map                        ← visualise connections (use anytime)
/arch-decide [node]              ← lock in a decision with rationale
/arch-status                     ← where are we, what's blocking

      ↓ repeat until all blocking nodes reach `ready`

/arch-finalize
      ↓ creates: .ai-arch/feature-briefs/NN-[slug].md
                 .ai-arch/todo-list.md

      ↓ each stage enters the implementation workflow:
        /interview or /deep-plan → /implement → /final-check
```

## When to Use Which Skill

| Situation | Skill |
|-----------|-------|
| Starting a new project from scratch | `/arch-init` |
| Want to see all nodes and their status | `/arch-explore` (shows dashboard) |
| Want to go deeper on a specific idea | `/arch-explore [node]` |
| Want to understand how ideas relate | `/arch-map` |
| Two ideas might be the same thing | `/arch-map [a] [b]` |
| Ready to commit to a direction | `/arch-decide [node]` |
| Want a progress snapshot | `/arch-status` |
| All blocking nodes are ready | `/arch-finalize` |

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
- `raw-idea → explored` : `/arch-explore`
- `explored → decided`  : `/arch-decide`
- `decided → ready`     : `/arch-decide` (when all open questions resolved)

## Node Priority

| Priority | Meaning |
|----------|---------|
| `blocking` | Must reach `ready` before `/arch-finalize` can run |
| `core` | Central to the product, should be decided before finalize |
| `extension` | Valuable but not required for first implementation pass |
| `deferred` | Consciously set aside — will not appear in todo list |

**Gate rule:** `/arch-finalize` requires all `blocking` nodes to be at `ready`.
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
    01-foundation.md          ← output of /arch-finalize
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
/arch-init                          /interview
/arch-explore          ──────→      /deep-plan
/arch-map           feature-brief   /implement phase-N
/arch-decide                        /review
/arch-status                        /final-check
/arch-finalize                      /document-work-result
                                    /update-kb-document
                                    /compact-work
```

Feature briefs from `/arch-finalize` are the handoff point.
Each brief is the starting input for one run of the implementation workflow.

## Tips

- **Run `/arch-map` early and often.** Even with raw-idea nodes, it surfaces hidden dependencies and merge candidates before you go deep on the wrong thing.
- **Don't rush to `/arch-decide`.** A premature decision on a poorly explored node creates false certainty. Explore first.
- **Blocking nodes first.** Tech stack, core data model, platform choice — these unblock everything else. Run `/arch-status` to see the dependency chain.
- **Use deferred honestly.** If an idea won't affect the first implementation pass, mark it deferred. It keeps the map clean and finalization reachable.
- **Feature briefs don't need to be complete.** If a brief has open technical questions, that's fine — `/interview` will resolve them. The brief just needs enough context to start the conversation.
- **The todo list is a living document.** Update the status column as stages complete. It becomes your project log.
