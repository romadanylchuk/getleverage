# test-suite

Universal test-authoring workflow for Claude Code. Turns a test case (markdown file or todo entry) into a high-quality automated test through a controlled, multi-stage process — and grows a project knowledge base organically as you work, rather than demanding heavy upfront investment.

The skills are deliberately **tech-agnostic**: independent of programming language, testing framework, product domain, and whether or not source code is accessible. All product- and stack-specific knowledge lives in a per-project knowledge base under `kb/`. The skills themselves encode procedure and discipline, not domain facts.

## Skills

| Skill | Stage | Role |
|---|---|---|
| `/test-suite:test-kb-bootstrap` | setup | Initialize and incrementally populate `kb/` from available sources (docs, existing tests, API specs, code). Conservative — never invents content, never overwrites human-validated sections (`source: manual` or `source: gap-resolution`). |
| `/test-suite:test-brief` | per case | Analyze a single test case, produce a combined brief + implementation plan, surface knowledge gaps with three resolution paths (answer / mark blocked / allow assumption). |
| `/test-suite:test-implement` | per case | Write the test code following the brief, reusing existing helpers and conventions. Stops and reports if the brief turns out to be inadequate — never improvises. |
| `/test-suite:test-verify` | per case | Verify the test passes against the working product **and** fails when the product is broken (lightweight mutation check on every test, full mutation check on high-criticality areas per `risk-map.md`). |

## Pipeline

```
test-kb-bootstrap   ── once per project, re-run when new sources arrive
        │
        ▼
   ┌─ pending ─────► test-brief ──► briefed ──► test-implement ──► implemented ──► test-verify ──► verified
   │                     │                                                                            │
   │                     ├─► blocked (knowledge gap)                                                  │
   │                     └─► not_automatable                                                          │
   │                                                                                                  │
   └──────────────────────────── todo.json (shared queue contract) ◄─────────────────────────────────┘
```

There is no orchestrator skill. Skills are invoked one case at a time, in three ways:

1. **Case-by-case (user-directed):** "brief TC-1234" → `/test-suite:test-brief TC-1234`.
2. **Queue-aware agent:** "process the next pending case" — Claude reads `todo.json`, picks the right skill for the case's status, and invokes it. No orchestrator needed; this is natural agent behavior given the shared queue contract.
3. **Batch (`run-queue` CLI):** for headless / unattended runs, an optional CLI helper (~50–100 lines) loops through the queue and shells out to `claude -p` per case.

## Shared artifacts

| File | Purpose |
|---|---|
| `kb/` | Project knowledge base, layered by concern (`product-spec.md`, `observable-surface.md`, `helpers.md`, `patterns.md`, `anti-patterns.md`, `conventions.md`, `risk-map.md`) plus a generated `index.json`. |
| `todo.json` | Shared work queue. Every skill reads it, every skill writes its own status transitions per the Queue Contract. |
| `kb-gaps.md` | Persistent record of knowledge gaps with explicit `kind` (`hard` blocking, `soft` proceeded-under-assumption, `kb-completeness` meta). Deduplicated within kind — repeat references increment a gap's `related_cases` rather than creating duplicates, so frequency becomes a priority signal. |
| `kb-drift.md` | Divergences between kb conventions and what existing tests actually do, recorded by `test-implement` and surfaced by the next `test-kb-bootstrap` run for human resolution. |
| `briefs/{case_id}.brief.md` | Combined brief + implementation plan. Output of `test-brief`, input to `test-implement`. Rejected briefs are renamed to `briefs/{case_id}.brief.rejected.md` so a re-brief has context. |
| `verify/{case_id}.verify.md` | Verification report. Output of `test-verify`, tracked via `artifacts.verify` in `todo.json`. |
| `.test-suite/last-write/{case_id}.sha256` | Sidecar SHA recorded by `test-implement` so `test-verify` can confirm the test file is byte-for-byte unchanged after mutation checks. |

## Design contract

The full design — kb layering, section metadata format, gap log lifecycle, queue contract, mutation-check policy, universality requirements — lives in [doc/test-skills-brief.md](../../doc/test-skills-brief.md) at the repo root.

## License

MIT
