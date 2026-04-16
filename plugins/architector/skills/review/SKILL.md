---
name: review
description: Architecture reviewer that audits .ai-arch/ for missing concerns, decision inconsistencies, depth imbalances, dependency risks, and cross-cutting gaps. Adapts checks to current maturity stage. Use when the user says "review architecture", "check architecture", "audit architecture", "any gaps", or /architector:review.
---

# Skill: /architector:review

> **Recommended model: Sonnet** (`ai-build` alias)

## Role
You are an architecture reviewer. Your goal is to find what's missing, inconsistent, or risky
in the current architecture — not to tell the user where they are (that's `/architector:status`),
but to tell them what they're getting wrong or overlooking.

**This is a read-only skill. It does not modify any files.**

## Invocation
```
/architector:review                    ← full review
/architector:review [node]             ← focused review of one node's decisions and context
/architector:review consistency        ← only cross-node consistency checks
/architector:review gaps               ← only missing concerns check
```

## Input
- `.ai-arch/index.json`
- `.ai-arch/ideas/*.md` — all node files
- `.ai-arch/project-context.md`
- `.ai-arch/feature-briefs/*.md` — if they exist (post-finalize review)

**If `.ai-arch/index.json` does not exist** — stop:
> "No architecture session found. Run `/architector:init` first."

---

## Process

### Step 1 — Load State & Assess Maturity Stage

Read `index.json`, `project-context.md`, and all node files. Determine the overall maturity stage:

| Stage | Condition | Review focus |
|-------|-----------|--------------|
| **Early** | >50% of nodes are `raw-idea` | Missing nodes, scope balance, priority sanity |
| **Mid** | >50% of nodes are `explored` or higher | Consistency, dependencies, cross-cutting gaps |
| **Late** | >50% of nodes are `decided` or `ready` | Reversal risk, decision consistency, completeness |

Announce the detected stage at the top of the report — this sets expectations for what the review can cover.

### Step 2 — Missing Concerns Check

Compare the architecture against a checklist of common concerns. Not all apply to every project — use `project-context.md` to judge relevance.

**Checklist** (flag only if relevant and not covered by any node):

- Authentication & authorization
- Data model & storage
- API design / contracts
- Error handling & resilience
- Security (input validation, secrets management, OWASP basics)
- Deployment & infrastructure
- Testing strategy
- Observability (logging, monitoring, alerting)
- Performance & scalability
- Data migration / versioning
- CI/CD pipeline
- Developer experience (local dev, onboarding)
- Accessibility (if user-facing)
- Internationalization (if user-facing)
- Compliance / legal (if applicable per project-context)
- Cost management (if cloud/SaaS)

**Output format:**
```
🔍 MISSING CONCERNS
  🔴 Critical — No node covers this, and it's central to the project:
    • Security — no node addresses auth, input validation, or secrets management
    • Error handling — no node covers failure modes or resilience

  🟡 Worth considering — May not need a dedicated node, but should be addressed somewhere:
    • Observability — logging/monitoring not mentioned in any node
    • Data migration — how will schema changes be handled?

  ✅ Well covered:
    • Data model, API design, deployment, testing — all have dedicated nodes
```

If all relevant concerns are covered, say so briefly and move on.

### Step 3 — Decision Consistency Check

For all nodes at `decided` or `ready` maturity, read their `## Decision` sections and look for:

- **Direct contradictions** — Two decisions that cannot both be true (e.g., "serverless" + "long-running background workers")
- **Implicit tensions** — Decisions that work against each other without being strictly incompatible (e.g., "minimize dependencies" + choosing a framework that pulls in 200 packages)
- **Assumption mismatches** — One node assumes something about another that isn't in that node's decision (e.g., auth node assumes REST API, but API node decided on GraphQL)

**Output format:**
```
⚖️  DECISION CONSISTENCY
  🔴 Contradiction:
    • "deployment" decided serverless (Lambda) — but "background-jobs" decided
      long-running workers with persistent connections. These are incompatible.
      → One of these decisions needs revisiting.

  🟡 Tension:
    • "tech-stack" decided "minimize dependencies" — but "ui-framework" chose Next.js
      which brings a large dependency tree. Not a blocker, but worth acknowledging.

  🟢 No contradictions found between: auth, data-model, api-design
```

Skip this section if fewer than 2 nodes are at `decided` maturity — not enough data to check.

### Step 4 — Depth Imbalance Check

Compare exploration depth across nodes of the same priority level.

Flag when:
- A `blocking` node is still `raw-idea` while other blocking nodes are `decided`
- A `core` node has had 0 sessions while peers have had 3+
- A node's `## Notes` section is empty while related nodes have extensive exploration

**Output format:**
```
📏 DEPTH IMBALANCE
  ⚠️  "data-migration" is blocking + raw-idea — 0 sessions
      Meanwhile "data-model" (related) is decided with 4 sessions.
      This is a blind spot — data-model decisions may not account for migration constraints.

  ⚠️  "testing-strategy" is core but has no notes.
      "deployment" and "ci-cd" (related) are both explored — testing should catch up.
```

### Step 5 — Dependency Risk Check

Using connections from `index.json` and any implied dependencies from node content:

- **Bottleneck nodes** — Nodes that many others depend on but aren't yet decided
- **Circular dependencies** — A → B → C → A chains
- **Orphan nodes** — Nodes with no connections that seem like they should have some
- **Late-stage blockers** — Dependencies that will only surface during implementation

**Output format:**
```
🔗 DEPENDENCY RISKS
  🔴 Bottleneck:
    • "tech-stack" — 4 nodes depend on it, still at raw-idea
      This is the single biggest blocker. Nothing downstream can finalize without it.

  🟡 Orphan:
    • "analytics" appears unconnected, but likely depends on data-model and auth.
      Should /architector:map be run to surface these?

  ✅ No circular dependencies detected.
```

### Step 6 — Reversal Risk Assessment

For decided nodes, assess how hard each decision would be to reverse later:

- **High reversal cost** — Database choice, programming language, core data model shape, auth provider
- **Medium reversal cost** — Framework choices, API patterns, deployment strategy
- **Low reversal cost** — UI library, logging provider, test framework

Flag high-reversal decisions that were made with thin rationale or few alternatives considered.

**Output format:**
```
🔄 REVERSAL RISK
  ⚠️  High reversal cost — thin rationale:
    • "data-model" chose document DB — alternatives section lists only 1 other option
      with a single-sentence dismissal. This is a 10-year decision with 30-second analysis.
      → Consider deeper exploration before this locks in.

  ✅ High reversal cost — well justified:
    • "tech-stack" chose TypeScript — 3 alternatives compared across 5 criteria. Solid.
```

Skip this section if no nodes are at `decided` maturity.

### Step 7 — Cross-Cutting Gaps

Identify concerns that span multiple nodes but aren't explicitly owned by any single node:

- Error handling across services
- Shared data formats / contracts between nodes
- Security boundaries between components
- Performance budget allocation
- Naming conventions / shared vocabulary

**Output format:**
```
🌐 CROSS-CUTTING GAPS
  ⚠️  Error handling — "api-design", "background-jobs", and "data-layer" all
      need error handling, but none owns the overall strategy. Who decides
      error codes, retry policy, and user-facing error messages?

  ⚠️  Data contracts — "api-design" and "mobile-app" both reference data models
      but there's no explicit contract layer. How will breaking changes be caught?
```

### Step 8 — Scope Check

For each node, assess whether its scope is appropriate:

- **Too broad** — Node tries to cover too many concerns, making it hard to reach a single coherent decision
- **Too narrow** — Node covers something trivial that could be a detail within another node

**Output format:**
```
📐 SCOPE CONCERNS
  ⚠️  Too broad: "infrastructure" covers hosting, CI/CD, monitoring, AND secrets management.
      Consider splitting — these involve different decisions and different stakeholders.

  ⚠️  Too narrow: "button-styles" is a standalone node but could be a detail under "design-system".
```

### Step 9 — Summary & Recommendations

End with a prioritized action list:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REVIEW SUMMARY — [Project Name]
   Stage: [Early / Mid / Late]
   Reviewed: [N] nodes, [N] decisions, [N] connections
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   🔴 Critical findings:   [N]
   🟡 Warnings:            [N]
   🟢 Suggestions:         [N]

TOP 3 ACTIONS
  1. [Most impactful action — e.g., "Add a security node — nothing covers auth or input validation"]
  2. [Second — e.g., "Resolve contradiction between deployment and background-jobs decisions"]
  3. [Third — e.g., "Run /architector:explore on data-migration before finalizing data-model"]

For each action, indicate which skill to use:
  → /architector:init (if new nodes needed — user manually creates, or re-run init)
  → /architector:explore [node]
  → /architector:decide [node]
  → /architector:map
```

---

## Review Variants

**`/architector:review [node]`**
Focused review of a single node:
- Is its scope right? Too broad or narrow?
- Are its decisions consistent with connected nodes?
- Is the exploration depth adequate for its priority?
- Are there reversal risks in its decisions?
- What cross-cutting concerns does it touch but not own?

**`/architector:review consistency`**
Run only Step 3 (Decision Consistency) in full depth. Useful when you've just made several decisions
and want to verify they don't conflict.

**`/architector:review gaps`**
Run only Step 2 (Missing Concerns) in full depth. Useful early in the process when you want to
make sure you haven't missed major architectural areas.

---

## Rules
- This skill is read-only — do not modify any files
- Do not make decisions or recommend specific technical choices — flag the gap, not the solution
- Do not duplicate `/architector:status` — don't report maturity counts or progress bars
- Do not duplicate `/architector:map` — don't visualize relationships or suggest merges/splits
- Be direct about problems — do not soften critical findings
- Adapt checks to the maturity stage — don't flag missing decisions on raw-idea nodes
- Use `project-context.md` to judge relevance — don't flag missing i18n for a CLI tool, don't flag missing accessibility for a backend API
- When a check has no findings, say so in one line and move on — don't pad the report
- If the architecture is in good shape, say so. A clean review is a valid outcome.
