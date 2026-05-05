---
name: test-kb-bootstrap
description: Initialize or incrementally update a test-automation knowledge base (kb/) for a project, populating layers — product-spec, observable-surface, helpers, patterns, conventions, risk-map, anti-patterns — from available sources (docs, existing tests, API specs, source code). Make sure to use this skill whenever the user wants to "bootstrap the kb", "set up the test knowledge base", "initialize tests for a new project", "ingest test docs", "scan existing tests into the kb", "update the kb after we got new specs", or whenever you encounter a project where /test-suite:test-brief is about to run but no kb/ folder exists yet. Conservative — never overwrites manual or gap-resolution sections, never invents content, safely re-runnable.
---

# Skill: /test-suite:test-kb-bootstrap

> **Recommended model: Sonnet** for routine bootstrapping. Reach for **Opus** if the project has dense product docs that need careful summarization into `product-spec.md` and `observable-surface.md`.

## Role

Set up the project's testing knowledge base — `kb/` plus `kb/index.json` — by inventorying available sources and populating the appropriate layers. The kb is what every other test-suite skill (`/test-suite:test-brief`, `/test-suite:test-implement`, `/test-suite:test-verify`) reads to make decisions, so the quality of the bootstrap shapes everything downstream.

This skill is **conservative by design**: it never overwrites human-validated content (`source: manual` or `source: gap-resolution`), never invents information, and never tries to be complete. The kb is meant to grow organically through the gap-resolution flow inside `/test-suite:test-brief`. Bootstrap just gives that loop a useful starting point.

## Inputs

A working directory that may or may not already have a `kb/` folder. The skill discovers sources or asks the user to point at them:

- Product/feature documentation (markdown, PDF, HTML)
- Existing test files (any language, any framework)
- API specifications (OpenAPI/Swagger, GraphQL schemas)
- Source code (if accessible)
- Network recordings (HAR files)
- User-provided notes or briefs

If no sources are available beyond the user's verbal description, scaffold templates only — do not fabricate content.

## Mode detection

Two modes, chosen at the start:

- **`with-source`** — source code is accessible. In addition to documentation, you can extract observable surface from code (events emitted, exposed APIs, public state shape), helper inventories from existing tests, and product behavior from implementation when docs are sparse.
- **`black-box`** — source code is NOT accessible (e.g., testing a third-party product). Rely on documentation, API specs, recorded network traffic, and the deployed UI's visible surface. **Do not pretend to have information you don't.** If a layer can't be populated from black-box sources, leave it as a template with prompts.

If the user doesn't specify, scan the working directory for source roots — the conventional names vary by ecosystem (e.g., `src/`, `lib/`, `app/`, `packages/`, `cmd/`, `internal/`, `main/java/`, `firmware/`, `Sources/`). If a plausible root is found, default to `with-source`. If not, ask the user before defaulting to `black-box` — silent fallback masks misconfiguration.

## Process

### 1. Inventory inputs

List every available source. Output a short summary — for example:

```
Sources detected:
- Product docs: docs/product/*.md (12 files)
- Existing tests: tests/**/*.spec.* (37 files)
- API spec: api/openapi.yaml
- Source code: src/ (with-source mode)
- No HAR files found
```

**Confirm with the user before processing** — they may add sources you missed (a Confluence link, a private wiki) or remove ones you shouldn't ingest. If invoked non-interactively (e.g., from a script with no user attached), proceed with the auto-detected list and write the inventory into the bootstrap report so a human can audit it.

### 2. Detect existing kb and reconcile

If `kb/` already exists, this is an **update run**, not a fresh bootstrap. Three rules govern what you may touch:

- **`source: manual` sections are immutable.** Never overwrite them.
- **`source: gap-resolution` sections are immutable.** They represent answers a human gave during briefing and must survive bootstrap re-runs. Never overwrite them.
- **`source: auto-bootstrap` sections** can be merged into. Match by `section_id` only — never by slug-of-title (titles can be renamed; section_ids are stable). See "Merge algorithm" below.

If no `kb/` exists, create the folder structure (see "KB layout") and proceed.

### 3. Populate by layer, in priority order

Process layers in this order, regardless of update vs. fresh bootstrap. Each layer's run is independent: a missing higher layer doesn't stop processing of lower layers, but lower layers may produce shallower output without higher-layer context.

| Order | Layer | Where it comes from |
|---|---|---|
| 1 | `product-spec.md` | Documentation. Highest priority — without it, downstream layers lack vocabulary. |
| 2 | `conventions.md` | Developer guides, README sections, CI config (test stack, where tests live, naming rules, how to run/debug). |
| 3 | `helpers.md` | Inventory of existing tests — parse imports, extract helper/fixture names, summarize from docstrings. |
| 4 | `observable-surface.md` | API specs, code analysis (`with-source` only), patterns in existing tests showing what is currently observed. |
| 5 | `patterns.md` | Recurring solutions detected across existing tests (waiting strategies, RNG seeding, isolation, auth helpers). |
| 6 | `risk-map.md` | **Template only**, with example categories and prompts. Do not invent risk classifications — that's team knowledge. |
| 7 | `anti-patterns.md` | **Empty template** with prompts for the team to fill in. Anti-patterns are deliberate team rejections, not derivable from sources. |

For each layer:
- If sources exist, write or merge sections per "Merge algorithm" below.
- If sources don't exist, write a template that explains what should go there and what would help the team contribute. **Templates are heading + prose only — do not include the metadata block** (the index regenerator silently ignores headings without metadata, which is the correct behavior here: templates aren't kb sections, they're scaffolds).
- A file that already contains any `manual` or `gap-resolution` sections is processed normally — those sections are skipped, but new auto-bootstrap content is merged into the same file. Do NOT skip the entire file.

### 4. Merge algorithm

When the layer-population step would write content that overlaps with an existing section:

1. Compute the candidate section's content from the source.
2. Look up the matching existing section **by `section_id`** in the file. If a candidate section's slug-of-title would collide with no existing id, generate a fresh id. If it would collide with an existing id under a different topic — extremely rare, but possible after manual editing — append a numeric disambiguator (e.g., `observable-surface.win-flow-2`) and warn in the bootstrap report.
3. If the matched existing section has `source: manual` or `source: gap-resolution`, **skip it**. Do not modify the body, the metadata, or `last_updated`.
4. If the matched existing section has `source: auto-bootstrap`:
   - Compute a hash of the existing body and the candidate body.
   - If hashes match, do nothing (no churn).
   - If hashes differ, replace the body with the candidate. Preserve `section_id`. Set `last_updated` to today. Keep `source: auto-bootstrap`.
5. If no existing section matches, write a new section with `source: auto-bootstrap`, today's `last_updated`, and a freshly generated `section_id`.

Sections in kb whose source material has been removed are **left in place**. Bootstrap does not delete content — that's a human decision.

### 5. Regenerate the index

Always invoke the bundled regenerator:

```
python <plugin>/skills/test-kb-bootstrap/scripts/regen_index.py <project-root>/kb
```

If the script exits non-zero, surface the error and abort. Do NOT fall back to in-place patching — the patch path skips broken-reference detection and lets index drift accumulate silently.

### 6. Produce a bootstrap report

Overwrite `kb-bootstrap-report.md` (do not append — re-runs should reflect current state, not history; for history, use `git log`). Cover:

- Mode used (`with-source` or `black-box`) and how it was determined.
- Which layers were populated and from which sources.
- Which layers remain template-only.
- Sections that were skipped because they were `manual` or `gap-resolution`.
- Section conflicts that required disambiguator suffixes (rare).
- What's missing that the team should fill in manually (especially `risk-map.md` and `anti-patterns.md`).
- Suggested next steps — typically: review auto-generated sections, fill the risk map, then start running `/test-suite:test-brief`.

The report is the user's roadmap for finishing the job.

## KB layout

```
<project-root>/
├── kb/
│   ├── product-spec.md          # What the product does, business logic, terminology
│   ├── observable-surface.md    # What can be observed externally (events, APIs, UI affordances, logs, state)
│   ├── helpers.md               # Catalog of existing test helpers, fixtures, utilities
│   ├── patterns.md              # How the team solves typical testing problems
│   ├── anti-patterns.md         # What the team deliberately avoids and why
│   ├── conventions.md           # Test stack, structure, naming, how to run, how to debug
│   ├── risk-map.md              # Categories of functionality and their criticality levels
│   └── index.json               # Generated index of all sections
├── kb-gaps.md                   # Unresolved knowledge gaps (created by /test-suite:test-brief)
├── kb-drift.md                  # Divergences detected by /test-suite:test-implement (optional, created on first divergence)
└── todo.json                    # Work queue (created by per-case skills)
```

## Layer responsibilities (cheat sheet)

- **`product-spec.md`** — what the product does and the vocabulary used to describe it. Without this, no skill can understand the *intent* of a test case.
- **`observable-surface.md`** — the most valuable layer for testing and the one most often missing from regular product docs. For each observable point: what it is, how to access it, whether it is stable, whether it is deterministic, known flakiness issues. Observable points include events, API responses, UI affordances, log signals, internal state hooks — whatever the product exposes for external scrutiny.
- **`helpers.md`** — inventory of existing test helpers, fixtures, page objects, mocks, builders. Each entry says when to use it and when not to. Without this, every new test reinvents wheels.
- **`patterns.md`** — the team's accepted solutions for recurring problems: waiting for async work, seeding RNG, isolating state between tests, handling authentication, and so on.
- **`anti-patterns.md`** — solutions the team has deliberately rejected, with reasons. Prevents regression to known-bad approaches.
- **`conventions.md`** — testing stack, folder structure, naming rules, how to run tests locally and in CI, how to debug failures, custom matchers/assertions.
- **`risk-map.md`** — taxonomy of product functionality by criticality. Used by `/test-suite:test-verify` to decide whether full mutation checks are required. Bootstrap creates a template; the team fills it in.

## Section format

Every section in every kb file starts with a level-2 (or deeper) markdown heading immediately followed by an HTML-comment metadata block. The HTML comment is invisible in rendered markdown but trivially parseable — this is what powers `kb/index.json`.

```markdown
## Win Animation Completion

<!--
section_id: observable-surface.win-animation-completion
tags: [animation, win-flow, async]
summary: How to detect that a winning animation has finished playing.
source: auto-bootstrap
last_updated: 2026-05-05
-->

The product emits an `animationComplete` event on the global event bus when …
```

Required metadata fields:
- `section_id` — stable identifier, formatted as `<file-stem>.<slug>` where `<file-stem>` is the filename without `.md` (e.g., `observable-surface`, `helpers`, `patterns`) and `<slug>` is a slug of the original title at creation time. **Never change `section_id` after creation** — gap entries and briefs reference it. Title can be renamed freely; the id stays put.
- `tags` — short list of strings, used for retrieval. May be empty (`[]`).
- `summary` — one sentence.
- `source` — one of `auto-bootstrap`, `gap-resolution`, `manual`.
- `last_updated` — ISO date (`YYYY-MM-DD`).

Optional metadata fields tools may add:
- `body_hash` — SHA-256 of the section body, used by bootstrap to detect unchanged content. Skills writing sections SHOULD compute and store this; skills updating sections MUST recompute it on body change.

When updating an existing `auto-bootstrap` section whose topic is unchanged, preserve `section_id`, refresh `last_updated` only if the body changed, and merge per the Merge algorithm above. Never change `source` to `manual` — that marker is reserved for content humans write or edit by hand.

## Critical constraints

- **Never overwrite `source: manual` sections.** They are immutable.
- **Never overwrite `source: gap-resolution` sections.** They are immutable for the same reason: a human committed an answer to them.
- **Never invent content.** If a layer has no source material, write a template with prompts, not fabricated facts. Fabrication produces flaky tests and wasted gap-resolution sessions downstream.
- **Be conservative on `risk-map.md` and `anti-patterns.md`.** These encode team judgment that can't be extracted from docs or code.
- **Be safely re-runnable.** Running this skill twice on the same inputs must produce no harmful changes — only updates where source content has actually changed.
- **Never delete sections.** Source material rotation is a human-judgment call.

## Universality

This skill must work for any project regardless of language, framework, or domain. Avoid assumptions like "the product is a web app" (could be API, mobile, desktop, embedded, or a CLI tool with no UI), "tests are in JavaScript" (could be any language), "source roots are under `src/`" (varies by ecosystem). Mirror the project's own vocabulary — extracted from sources — rather than imposing generic test-automation phrasing.

When examples are unavoidable, use diverse domains — alternate between web UI, HTTP APIs, mobile, embedded — to reinforce that the skill is not pinned to any one stack.

## Bundled scripts

`scripts/regen_index.py` — walks `kb/*.md`, parses HTML-comment metadata blocks under each heading, and writes `kb/index.json`. Also detects broken references: any `section_id` referenced in `kb-gaps.md` or `briefs/*.md` that no longer exists in the kb (warnings printed to stderr, non-blocking).

Invoke after any kb mutation:

```bash
python <plugin>/skills/test-kb-bootstrap/scripts/regen_index.py <project-root>/kb
```

The script is also runnable standalone — other test-suite skills (and you, manually) can re-run it without going through this skill.

## Outputs

- Updated `kb/` folder with sections written or merged per the rules above.
- Regenerated `kb/index.json`.
- A bootstrap report at `kb-bootstrap-report.md` (overwriting any previous run's report).
- This skill does NOT touch `todo.json`. The queue belongs to the per-case skills.
- This skill MAY surface entries from `kb-drift.md` (written by `/test-suite:test-implement`) in the bootstrap report so a human can resolve kb/test divergences. Bootstrap does NOT auto-resolve drift — that's a human decision.
