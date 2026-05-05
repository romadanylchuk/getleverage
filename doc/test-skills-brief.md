# Test Automation Skills Suite — Implementation Brief

## Context

This brief describes a suite of skills for an AI-assisted test authoring workflow. The skills mirror the philosophy of an existing product-development workflow (interview → plan → implement → review → final-check) but are adapted to the specifics of test automation, where the source of truth is a test case rather than open-ended product requirements.

The skills must be **universal**: independent of programming language, testing framework, product domain, and whether or not source code is accessible. All product-specific and stack-specific knowledge lives in a per-project knowledge base (kb). The skills themselves encode procedure and discipline, not domain facts.

## Goals

1. Turn a test case (markdown file or todo entry) into a high-quality automated test through a controlled, multi-stage process.
2. Make the quality of each stage observable and reviewable as a discrete artifact.
3. Build and maintain a project knowledge base that grows organically as work proceeds, rather than requiring heavy upfront investment.
4. Surface gaps in knowledge immediately, at the point where they matter, while preserving a record for batch resolution.
5. Verify not only that tests pass, but that they meaningfully catch regressions.

## Non-goals

- Coupling to any specific test framework, language, runner, or domain.
- Replacing human judgment on architectural decisions about the test suite as a whole.
- Generating tests in bulk without per-case review.
- Building a fully automated mutation-testing system (a lightweight version is included).

---

## Architecture Overview

Four skills, plus shared artifacts and an optional batch helper:

| Skill | Role |
|-------|------|
| `test-kb-bootstrap` | Initialize and incrementally populate the kb from available sources |
| `test-brief` | Analyze a single test case, produce a combined brief + implementation plan, surface knowledge gaps |
| `test-implement` | Write the test code following the brief, reusing existing helpers and project conventions |
| `test-verify` | Verify the test passes against the working product AND fails when the product is broken |

Plus:

- A **todo list** (`todo.json`) as the work queue across cases.
- A **gap log** (`kb-gaps.md`) as the persistent record of unresolved knowledge issues.
- A **kb index** (`kb/index.json`) as a generated lookup over the kb.
- An **optional CLI helper** (`run-queue`) for batch processing — see "Optional CLI Helper" below.

Skills are invoked one case at a time. There is **no orchestrator skill**: each skill takes a `case_id` (or path to a case file), does its work, and updates `todo.json` itself. Walking a queue and dispatching work is mechanical iteration, not reasoning — wrapping it as a skill would be a thin meta-layer over what is either natural agent behavior or a small CLI script.

Three ways to drive the queue:

1. **Case-by-case (user-directed):** the user names a case explicitly ("brief TC-1234") and invokes the appropriate skill.
2. **Queue-aware agent:** the user asks the agent to "process the next pending case"; the agent reads `todo.json`, picks the right skill for the case's status, and invokes it. No orchestrator needed — this is natural agent behavior given the shared queue contract.
3. **Batch (`run-queue` CLI):** for headless / unattended runs, the optional CLI helper loops through the queue and shells out to `claude -p` per case.

---

## Knowledge Base Structure

### Layout

```
kb/
  product-spec.md          # What the product does, business logic, terminology
  observable-surface.md    # What can be observed externally (events, APIs, DOM, logs, state)
  helpers.md               # Catalog of existing test helpers, fixtures, utilities
  patterns.md              # How the team solves typical testing problems
  anti-patterns.md         # What the team deliberately avoids and why
  conventions.md           # Test stack, structure, naming, how to run, how to debug
  risk-map.md              # Categories of functionality and their criticality levels
  index.json               # Generated index of all sections across all layers
kb-gaps.md                 # Unresolved knowledge gaps (root level)
todo.json                  # Work queue (root level)
```

### Layer responsibilities

**`product-spec.md`** — what the product does and the vocabulary used to describe it. Without this, no skill can understand the intent of a test case. This is typically the most populated layer after bootstrap.

**`observable-surface.md`** — the most valuable layer for testing and the one most often missing from regular product documentation. For each observable point: what it is, how to access it, whether it is stable, whether it is deterministic, known flakiness issues. This is what enables tests to verify the right thing rather than the convenient thing.

**`helpers.md`** — inventory of existing test helpers, fixtures, page objects, mocks, builders. Each entry describes when to use it and when not to. Without this layer, every new test reinvents wheels.

**`patterns.md`** — the team's accepted solutions for recurring problems: how to wait for async work, how to seed RNG, how to isolate state between tests, how to handle authentication, etc.

**`anti-patterns.md`** — solutions the team has deliberately rejected, with reasons. Prevents regression to known-bad approaches.

**`conventions.md`** — testing stack (framework, runner, assertion library), folder structure, naming rules, how to run tests locally and in CI, how to debug failures, custom matchers/assertions.

**`risk-map.md`** — taxonomy of product functionality by criticality. Used by `test-verify` to decide whether full mutation checks are required. Bootstrap creates a template; the team fills it in.

### Section format inside kb files

Every section within every kb file MUST start with a level-2 (or deeper) markdown heading immediately followed by an HTML comment containing metadata. Example:

```markdown
## Win Animation Completion

<!--
section_id: observable.win-animation-completion
tags: [animation, win-flow, async, dom]
summary: How to detect that a winning animation has finished playing.
source: gap-resolution
last_updated: 2026-04-12
-->

The game emits an `animationComplete` event on the global event bus when...
```

The HTML comment is invisible in rendered markdown but trivially parseable. This is the foundation of the index.

### `kb/index.json`

Generated, never hand-edited. Schema (one entry per section):

```json
{
  "layer": "observable-surface",
  "section_id": "observable.win-animation-completion",
  "title": "Win Animation Completion",
  "summary": "How to detect that a winning animation has finished playing.",
  "tags": ["animation", "win-flow", "async", "dom"],
  "file": "observable-surface.md",
  "anchor": "win-animation-completion",
  "source": "gap-resolution",
  "last_updated": "2026-04-12"
}
```

Index regeneration is a small script invoked by skills that modify the kb. The script also emits warnings when sections referenced by gaps or briefs disappear (broken references) — non-blocking, just informational.

### Stable `section_id`s

Section IDs MUST be stable and uniformly formatted as `<file-stem>.<slug>`, where `<file-stem>` is the kb file's name without `.md` (e.g., `observable-surface`, `helpers`, `patterns`) and `<slug>` is a slug of the section's original title at creation time. Examples: `observable-surface.win-animation-completion`, `helpers.login-as-user`, `patterns.wait-for-async-completion`.

They are referenced from gap entries, briefs, and possibly test files. Renaming a section's title must NOT change its id. Bootstrap and gap-resolution generate ids from a slug of the original title; humans editing kb manually keep the existing id. Tools (bootstrap merge, gap-resolution writes) match existing sections **by `section_id` only** — never by re-slugging the current title.

Optional metadata field: `body_hash` (SHA-256 of the section body). Bootstrap uses this to detect unchanged content across re-runs and avoid no-op `last_updated` churn.

### Source markers

Every section has a `source` field with one of:
- `auto-bootstrap` — generated from documentation/code by `test-kb-bootstrap`
- `gap-resolution` — added during brief stage when the user answered a knowledge gap
- `manual` — written by a human directly

Both `manual` and `gap-resolution` are **immutable** to bootstrap re-runs. `manual` is human-authored; `gap-resolution` is human-validated (the user gave the answer). Bootstrap may overwrite only `auto-bootstrap` sections.

---

## The Todo List (`todo.json`)

The work queue. Schema (array of entries):

```json
{
  "case_id": "TC-1234",
  "case_path": "test-cases/TC-1234.md",
  "status": "briefed",
  "artifacts": {
    "brief": "briefs/TC-1234.brief.md",
    "test": "tests/auth/TC-1234.spec.<ext>",
    "verify": "verify/TC-1234.verify.md"
  },
  "blockers": [],
  "notes": [
    {
      "stage": "brief",
      "ts": "2026-05-05T14:32:00Z",
      "message": "Briefed against observable-surface.session-cookie; criticality high (case-tag)."
    }
  ]
}
```

Field notes:
- `artifacts.brief` / `artifacts.test` / `artifacts.verify` are filled by their respective skills upon successful completion. Bounce-back paths clear the relevant artifact (e.g., test-implement bounce-back clears `artifacts.brief`).
- `notes` is an **append-only array** of structured entries `{stage, ts, message}`. Each skill appends; no skill overwrites. The forensic record across stage transitions matters and must not be destroyed by the next writer.
- The boolean `not_automatable` field has been removed in favor of the `status: not_automatable` enum value — the two-source representation was redundant.

### Status values

- `pending` — case has not been touched yet
- `briefed` — brief produced, ready for implementation
- `implemented` — test written, ready for verification
- `verified` — test passes meaningful verification, done
- `blocked` — case blocked on a knowledge gap, see `blockers` field
- `not_automatable` — case cannot be automated (with reason in `notes`)
- `failed` — verification failed, needs human attention

### Queue Contract

`todo.json` is a **shared contract** that all four skills read and update. Each skill is responsible for transitioning the queue after its own work, so the queue stays consistent regardless of how the skill was invoked (user-directed, queue-aware agent, or `run-queue` CLI).

**Every skill, on entry, MUST:**
1. Resolve its `case_id` argument to the entry in `todo.json` and read `case_path` + `artifacts`.
2. Verify the entry's `status` matches the stage this skill operates on. If not, bail out cleanly and report — never run the wrong stage. Specifically:
   - `test-brief` runs only on `pending` (or re-runs on `blocked` after a gap is answered, transitioning back via the gap-resolution flow).
   - `test-implement` runs only on `briefed`.
   - `test-verify` runs only on `implemented`.

**Status transitions each skill writes:**

| Skill | On success | On exceptional outcome |
|---|---|---|
| `test-brief` | `pending` → `briefed` (fills `artifacts.brief`, appends notes entry) | → `blocked` (fills `blockers` with `gap_id`, appends notes entry) or → `not_automatable` (appends notes entry) |
| `test-implement` | `briefed` → `implemented` (fills `artifacts.test`, appends notes entry) | → `pending` (brief inadequate; **clears `artifacts.brief`**, renames the brief to `briefs/{case_id}.brief.rejected.md`, appends notes entry describing what was missing) |
| `test-verify` | `implemented` → `verified` (fills `artifacts.verify`, appends notes entry) | → `failed` (fills `artifacts.verify`, appends notes entry with cause tag: `flaky-env` / `product-bug` / `test-bug` / `smell` / `restoration-failed`) |
| `test-kb-bootstrap` | does NOT touch `todo.json` directly | when a gap is answered (during a `test-brief` session), cases listed in the gap's `related_cases` move from `blocked` back to `pending` — see "Lifecycle when a gap is answered" |

**Entry-guard reconciliation.** Because the queue update is sequential after the artifact write, a process crash can leave the artifact on disk while the queue still claims an earlier stage. Each skill's entry guard reconciles this on next run:

- `test-brief` on `pending` with an orphaned `briefs/{case_id}.brief.md`: delete the orphan and re-process (unless the user passes `--keep-orphan`).
- `test-implement` on `briefed` with an existing test file: compare the file's SHA-256 to the sidecar at `.test-suite/last-write/{case_id}.sha256`. If sidecars match, skip implementation and update the queue. If they don't match, refuse — disk has unverifiable state.
- `test-verify` on `implemented` with a missing `artifacts.verify` but a leftover mutation backup at `.test-suite/mutation-backup/{case_id}.*`: restore the test from the backup, verify the SHA against the sidecar, then proceed.

Skills MUST use a temp-and-rename pattern when writing `todo.json` so a partial write can't corrupt the file. Do not leave the queue claiming `briefed` if the brief file isn't on disk.

**Re-execute paths.** Each per-case skill supports an explicit override for re-running on a non-matching status:
- `test-brief --rebrief` on `briefed` / `implemented` / `verified` (with `--allow-downstream-invalidation` when a downstream artifact already exists).
- `test-implement --reimplement` on `implemented` / `verified` (with `--allow-downstream-invalidation`).
- `test-verify --reverify` on `verified`.

Re-execute archives the previous artifact under a `.{N}` suffix and resets the relevant queue fields. Default behavior (no flag) is to refuse on a non-matching status — protecting committed work.

### Adding cases to the queue

Two ways:
- **Manual:** user invokes `test-brief` with a path to a test case markdown. If no `todo.json` exists, the skill creates one with this single entry. If `todo.json` exists and the case is not yet listed, append it as `pending`.
- **Semi-automatic (init helper):** for a folder of test case markdown files, the `run-queue init` sub-command (see "Optional CLI Helper") generates a fresh `todo.json` with one `pending` entry per file. Idempotent — re-running it adds new files only, never overwrites existing entries.

---

## The Gap Log (`kb-gaps.md`)

Persistent record of knowledge gaps discovered during work. Two-level recording:

**In `todo.json`** — minimal blocker reference per case (link to gap entry by id), so the queue stays scannable.

**In `kb-gaps.md`** — full entry per gap. Markdown with HTML-comment metadata, similar to kb sections. Schema:

```markdown
## How to detect win animation completion

<!--
gap_id: gap.2026-04-12.win-animation-completion
discovered_during: TC-1234
layer: observable-surface
kind: hard
status: open
related_cases: [TC-1234, TC-1238]
-->

**Question:** When checking that a win has been displayed, is there a deterministic
event/callback to wait for, or do we have to poll state, or wait by time?

**Already searched:**
- kb/observable-surface.md — no entry on animation events
- existing tests in tests/wins/ — they all use 2000ms sleeps, which feels like a workaround
- product docs section "Win Flow" — describes UX but not technical signals

**Resolution:** (filled when status becomes `answered`)
**Resolved into:** (filled with section_id when answer is added to kb)
```

### Status values for gaps

- `open` — unresolved
- `answered` — user provided an answer; recorded into kb; any blocked cases can resume
- `wont-fix` — user decided this gap won't be closed (e.g., the case is genuinely not automatable for this reason)

### Kind values for gaps

- `hard` — the gap blocks at least one case (recorded by `test-brief` Path 2). Cases listed in `related_cases` are in `status: blocked` until the gap is answered.
- `soft` — at least one case proceeded under explicit assumption (recorded by `test-brief` Path 3). The cases are NOT blocked; the gap is for follow-up validation. Answering it may invalidate an existing brief — surface the implication, but no automatic case requeue.
- `kb-completeness` — meta-gap recorded by any skill when the kb itself is missing structure (e.g., risk-map has no entry for a referenced area, conventions.md lacks a runner command, a related case file path is broken). Does NOT block individual cases. The team addresses these in batch.

### Deduplication

When a skill is about to record a new gap, it MUST first scan `kb-gaps.md` for `open` gaps **of the same kind** with overlapping subject (compare layer + tags + a deterministic similarity metric on the question text — implementer should pick one and document it; trigram or BM25 are both reasonable). If a match is found, the skill appends the current `case_id` to the existing entry's `related_cases` instead of creating a duplicate. This turns frequency of reference into a priority signal.

A hard gap and a soft gap on the same topic are **not duplicates** — they have different lifecycles and should be tracked separately. If a Path 3 (assumption) encounters an existing hard gap with the same subject, it appends the current `case_id` to the hard entry's `related_cases` (the case isn't blocked but is implicated) — it does NOT downgrade `kind` from hard to soft.

### Lifecycle when a gap is answered

When the user answers a gap during a brief session:
1. The skill writes the answer as a new section in the appropriate kb layer file with `source: gap-resolution` and `section_id: <file-stem>.<slug-of-title>`.
2. The skill regenerates `kb/index.json` by invoking the bundled regenerator script. **In-place JSON patching is not permitted** — it skips broken-reference detection and lets index drift accumulate silently.
3. The skill updates the gap entry: `status: answered`, fills `resolution` and `resolved_into` (the new section's id).
4. For `hard` gaps: any other cases in `related_cases` that were `blocked` on this gap are returned to `pending` for re-briefing — the answer may unblock them.
5. For `soft` gaps: cases in `related_cases` are NOT requeued automatically. The answer may invalidate one of their assumptions; the skill prints a heads-up listing those briefs so a human can decide whether to re-brief them.

---

## Skill 1: `test-kb-bootstrap`

### Purpose

Initialize the kb structure for a new project, or incrementally update an existing kb when new sources become available (new docs, new tests, updated API spec, etc.). Does NOT aim for completeness — the kb completes itself organically through gap resolution.

### Inputs

- A working directory that may or may not already contain a `kb/` folder.
- Available sources, which the skill discovers or the user points to:
  - Product/feature documentation (markdown, PDF, html)
  - Existing test files (any language, any framework)
  - API specifications (OpenAPI/Swagger, GraphQL schemas)
  - Source code, if accessible
  - Network recordings (HAR files), if available
  - User-provided notes or briefs

### Modes

The skill must support two modes, chosen by a flag or detected from inputs:

**`with-source`** — source code is available. Bootstrap can additionally extract observable surface from code (events emitted, exposed APIs, public state shape), helper inventories from existing tests, and product behavior from implementation when docs are sparse.

**`black-box`** — source code is NOT available (e.g., testing a third-party product). Bootstrap relies on documentation, API specs, recorded network traffic, and the surface visible through deployed UI. It must NOT pretend to have information it doesn't.

### Behavior

1. **Inventory inputs.** List what sources are available. Output a short summary so the user can confirm before processing.
2. **Detect existing kb.** If `kb/` exists, treat this as an update run. Existing sections are preserved; new content is merged in. Sections marked `manual` are NEVER overwritten.
3. **Populate by layer**, in this priority order:
   - `product-spec.md` from documentation. Highest priority — without it nothing else makes sense.
   - `conventions.md` from developer guides, README sections, CI config.
   - `helpers.md` from inventory of existing tests (parse imports, extract function/fixture names, summarize from docstrings).
   - `observable-surface.md` from API specs, code analysis (in `with-source` mode), patterns in existing tests showing what is currently observed.
   - `patterns.md` from recurring approaches detected across existing tests.
   - `risk-map.md` — create as a TEMPLATE only, with examples and prompts. Do not invent risk classifications.
   - `anti-patterns.md` — create as empty with prompts for the team to fill in.
4. **Write sections with metadata.** Every generated section must have the HTML-comment metadata block, with `source: auto-bootstrap` and `last_updated` set to today.
5. **Regenerate `kb/index.json`.**
6. **Produce a bootstrap report** to the user listing: which layers were populated and from which sources, which layers remain template-only, what's missing that the team should fill in manually, suggested next steps.

### Critical constraints

- NEVER overwrite sections marked `source: manual` — they are human-authored and immutable.
- NEVER overwrite sections marked `source: gap-resolution` — they are human-validated answers and are equally immutable. Bootstrap can only modify `source: auto-bootstrap` sections.
- Match existing sections **by `section_id`**, not by slug-of-current-title. Titles can be renamed (humans do this); ids stay stable.
- When merging into existing auto-generated sections, preserve `section_id`, refresh `last_updated` only if the body actually changed (compare via `body_hash`).
- Do NOT invent content. If a layer has no source material, leave it as a template with prompts (heading + prose only — no metadata block, since templates are scaffolds, not sections).
- Do NOT delete sections whose source material has rotated. Source rotation is a human-judgment call.
- Be conservative on `risk-map.md` and `anti-patterns.md` — these are team knowledge, not extractable from sources.
- The skill MUST be safely re-runnable. Running it twice in a row on the same inputs should produce no harmful changes.
- Surface entries from `kb-drift.md` (written by `test-implement`) in the bootstrap report so a human can resolve kb/test divergences. Bootstrap does NOT auto-resolve drift.

### Outputs

- Updated `kb/` folder.
- Regenerated `kb/index.json`.
- A bootstrap report (printed or saved to `kb-bootstrap-report.md`).

---

## Skill 2: `test-brief`

### Purpose

Take a single test case and produce a combined **brief + implementation plan** as one markdown artifact. Surface knowledge gaps to the user immediately, at the point of discovery, with three resolution paths: answer now, mark blocked, or allow assumption.

This is the central skill of the suite. Its quality determines the quality of everything downstream.

### Inputs

- A test case: either a path to a markdown file, or a `case_id` that the skill resolves from `todo.json`.
- The kb (read-only for analysis; writable when resolving gaps).
- The gap log (read-write).
- Optionally: the path to existing tests for stylistic/structural reference.

### Behavior

The skill processes the case through four analytical layers. For EACH layer, it first attempts to find answers in available artifacts; only when an answer cannot be reasonably extracted does it surface a gap to the user.

#### Layer 1: Intent

What is this test case really verifying? What breaks for users if this functionality is broken? The literal scenario is the surface; the intent is what makes assertions meaningful. Pull from product-spec, the test case text, related cases, the risk map.

#### Layer 2: Observable surface

What can be observed externally to verify the intent? Which events, APIs, DOM elements, state values, logs are available? For each, is it stable and deterministic? Pull from observable-surface, existing tests, code (if available).

#### Layer 3: Determinism

Where in the scenario are non-deterministic elements (animations, RNG, network, race conditions)? What does the project's pattern library say about handling each? Where will explicit waits, seeds, or mocks be needed?

#### Layer 4: Boundaries

What is this test deliberately NOT verifying? What's covered by sibling tests? What edge cases are out of scope? Without this, tests sprawl.

### Pre-question discipline

Before asking the user ANY question, the skill must demonstrate it has done the work:

1. Searched the relevant kb layer (using the index for efficiency).
2. Searched existing tests for similar scenarios.
3. Examined source code or API specs if available.
4. Re-read the test case and any linked cases.

Questions to the user MUST include:
- The specific question, narrowly scoped.
- A summary of what was already searched and found.
- Why the search was insufficient.

Bad question: "How do I check that the user is logged in?"
Good question: "I need to verify the user is logged in after the auth flow. I checked observable-surface (no auth-related entries), existing tests in tests/auth/ (they use a `loginAsUser` helper but don't verify the resulting state explicitly), and source code is not accessible. Is there a deterministic signal — a cookie, a stored token, a UI element — that indicates logged-in state, or should I rely on attempting an authenticated action?"

### Gap resolution flow

When a gap surfaces, the skill performs **one** dedup scan against `kb-gaps.md` (matching by kind + layer + tags + question similarity) BEFORE branching into resolution paths. The match result is reused by whichever path the user picks.

The user then has three response paths:

1. **Answer directly.** The skill:
   - Continues the brief with the answer.
   - Writes the answer as a new section in the appropriate kb layer (with `source: gap-resolution`).
   - Regenerates `kb/index.json` via the bundled script (no in-place patching).
   - If the dedup scan found a matching open gap, marks it `answered` and fills resolution fields; if it was a `hard` gap, returns its `related_cases` from `blocked` to `pending`. If the dedup scan found no match, no gap-log entry is created — the new kb section's `source: gap-resolution` marker is the audit trail.

2. **Mark blocked.** The skill:
   - Records the gap in `kb-gaps.md` with `kind: hard` (or appends `case_id` to a matched existing hard entry).
   - Updates the case's status in `todo.json` to `blocked` with a reference to the gap id.
   - Stops processing this case and exits with a clear summary of which gap is blocking it.

3. **Allow assumption.** The skill:
   - Continues the brief with an explicit assumption, marked clearly in the artifact ("ASSUMPTION: ...").
   - Records a `kind: soft` gap entry in `kb-gaps.md` for follow-up validation (or appends `case_id` to a matched existing soft entry; if the matched entry is hard, appends to its `related_cases` without downgrading the kind).
   - Proceeds.

The skill does NOT offer a "skip silently" option.

### Brief artifact format

The output is a markdown file at `briefs/{case_id}.brief.md` with these required sections:

```markdown
# Brief: {case_id} — {short title}

## Criticality
- Level: low | medium | high
- Source: explicit case-tag | risk-map heuristic | default
- Mapped product area(s): [<name>, ...]

## Intent
What this test really verifies. Why it matters.

## Observable Points
The specific signals this test will use, with references to kb section_ids. For each, note stability and determinism.

## Determinism Notes
Non-deterministic elements and how they will be handled. Reference patterns from kb/patterns.md by section_id.

## Boundaries
What this test does NOT cover. Related tests/cases.

## Implementation Outline
- File location and naming
- Setup/teardown approach (referencing existing helpers from kb by section_id)
- Step-by-step structure of the test
- Specific assertions and their justifications — each must map back to an Observable Point above
- Any new helpers/fixtures that need to be created (with rationale)

## Assumptions
Explicit list of assumptions made during analysis (from "allow assumption" gap responses). Each tagged with what would invalidate it.

## References
- Test case: {path}
- KB sections used: [section_id, ...]
- Existing tests referenced for style: [paths]
- Related cases: [case_ids]
- Re-brief context: <present only when --rebrief was used; names the previous brief at briefs/{case_id}.brief.{N-1}.md and summarizes the prior bounce-back reason from todo.json notes>
```

The `## Criticality` field is required so `/test-suite:test-verify` can determine criticality without re-parsing prose. `Mapped product area(s)` are the matchable inputs against `kb/risk-map.md` categories.

### Not-automatable detection

If, after analysis, the skill determines the case cannot be automated (requires real hardware, real video stream, manual visual judgment, etc.), it sets the case status to `not_automatable` with a clear reason in `notes`. It does NOT produce a brief in this case.

### Outputs

- A brief file at `briefs/{case_id}.brief.md` — OR a `not_automatable` / `blocked` status update.
- Updates to `todo.json` reflecting new status.
- Updates to `kb/` and `kb/index.json` if any gaps were resolved.
- Updates to `kb-gaps.md` if any gaps were recorded.

---

## Skill 3: `test-implement`

### Purpose

Write the actual test code following the brief, reusing existing helpers and conventions from the kb.

### Inputs

- A brief at `briefs/{case_id}.brief.md`.
- The kb (read-only).
- Existing test files for stylistic reference.
- The original test case file.

### Behavior

1. **Read the brief in full.** This is the source of truth for what to write.
2. **Cross-reference the kb** for helpers, patterns, conventions named in the brief.
3. **Read at least 2-3 existing tests** in the same area to match style — naming, file structure, setup/teardown idioms, assertion style.
4. **Write the test** following the implementation outline. New helpers/fixtures introduced should match existing patterns.
5. **If the brief turns out to be wrong or incomplete during implementation**, the skill MUST:
   - Stop writing.
   - Discard any partial test file.
   - Update the case status back to `pending`, **clear `artifacts.brief`**, and rename the brief file to `briefs/{case_id}.brief.rejected.md` (so a re-brief has context).
   - Append a structured notes entry describing what was missing (`{stage: "implement", ts, message, suggested_fix?}`).
   - Report to the user with the issue.
   - NOT silently fix the brief or guess.

6. **If the kb conflicts with what existing tests actually do**, the skill MUST NOT mutate the kb. It records the divergence in `kb-drift.md` (project root) and follows the codebase's pattern for this single implementation. The next bootstrap run surfaces drift entries for human resolution.

### Output

- A test file at the location specified in the brief.
- Possibly new helpers/fixtures, if the brief specified them.
- Updates to `todo.json`: status → `implemented`, `artifacts.test` filled in.

### Critical constraints

- Do not invent helpers that already exist in the kb. If unsure, search the helper catalog. If you discover the brief authorized a new helper but an equivalent already exists, bounce back rather than build a duplicate.
- Do not deviate from naming/structural conventions in `conventions.md` without explicit reason. If the codebase deviates from `conventions.md`, follow the codebase and record the divergence in `kb-drift.md` — never edit kb sections directly.
- Do not add assertions beyond what the brief specifies. Scope discipline is part of test quality.
- If new helpers are added, document them: append a section to `helpers.md` with `source: manual` (so it's not overwritten by future bootstrap runs).
- After writing the test, store its SHA-256 at `.test-suite/last-write/{case_id}.sha256` so `test-verify` can confirm post-mutation file integrity.
- This skill never edits existing kb sections. The only kb mutation it performs is appending a `source: manual` helper section when authorized.

---

## Skill 4: `test-verify`

### Purpose

Verify that the test (a) passes against the working product and (b) actually catches regressions. The second part is what distinguishes a real verification from a sanity check.

### Inputs

- A test file produced by `test-implement`.
- The brief (for criticality determination via referenced product areas).
- The kb, especially `risk-map.md` and `observable-surface.md`.

### Behavior

1. **Run the test.** It must pass. If it fails:
   - Diagnose: flaky env, actual product bug discovered, or test bug.
   - Mark case `failed` with `artifacts.verify` filled, append a notes entry tagged with the cause (`flaky-env` / `product-bug` / `test-bug`).

2. **Lightweight mutation check (always).** Before mutating, copy the test file to `.test-suite/mutation-backup/{case_id}.{ts}.bak`.
   - Identify the **headline assertion**: the assertion mapped to the first Observable Point in the brief (source order if multiple).
   - Mutation A: change an expected value within the headline assertion to something obviously wrong; the test must fail.
   - Mutation B: neutralize the headline assertion (comment out, replace with a no-op equivalent in the runner); the test must fail or error.
   - Restore from the backup. Recompute the test's SHA-256 and compare to `.test-suite/last-write/{case_id}.sha256`. They must match exactly. If they don't, refuse to mark the case successful — surface "verification corrupted the test file."
   - For zero-assertion tests, the lightweight check is NOT skippable — the verdict is `failed` with `smell: no-assertions`.

3. **Determine criticality** from the brief's `## Criticality` field (populated by `test-brief`). Fallback to the two-source heuristic only for legacy briefs lacking this section. If no source determines a level, default to `medium` and record a `kb-completeness` gap.

4. **Full mutation check (high-criticality only).** Maintain a manifest of perturbations and explicit inverses. For each Observable Point in the brief, design a perturbation (drop event, suppress state change, return wrong-shape response, suppress side effect). Each must cause the test to fail.
   - After all perturbations are validated, walk the manifest in reverse and execute every inverse. **Verify each inverse succeeded** (probe the surface, compare config to a snapshot, etc.). A residual mock or unrestored fixture is `restoration-failed` — the verdict is `failed`.
   - If breaking the observable surface is impossible (black-box product, no mocking infrastructure), record this as a verification limitation, not a failure. The verdict is still `verified` provided the lightweight check passed; the report flags exactly which Observable Points were not full-mutation-verified.

5. **Report.** Output a verification report at `verify/{case_id}.verify.md` with a machine-readable HTML-comment header (verdict, cause, criticality, generated_at) plus structured sections per the verify skill format.

### Criticality determination

Read the brief's `## Criticality` field directly. For legacy briefs without this field, fall back to the two-source heuristic:
- Primary: explicit priority/severity tag in the test case if present.
- Secondary: deterministic similarity match against `risk-map.md` categories using the brief's referenced product areas.

If both are absent, default to `medium` and record a `kb-completeness` gap (`risk-map needs entry for X`).

### Output

- Verification report at `verify/{case_id}.verify.md`.
- Updates to `todo.json`: status → `verified` or `failed`, fills `artifacts.verify`, appends a structured notes entry. `notes` is append-only.
- Possibly a `kb-completeness` gap in `kb-gaps.md` (criticality couldn't be determined; runner command missing from `kb/conventions.md`).

### Critical constraints

- The test file on disk after this skill exits MUST match the SHA-256 sidecar at `.test-suite/last-write/{case_id}.sha256` byte-for-byte. If it doesn't, the queue is not updated to a successful state; restore from the backup at `.test-suite/mutation-backup/{case_id}.{ts}.bak` and try again, or refuse and surface for human intervention.
- Every observable-surface perturbation has an explicit inverse in the manifest, every inverse is executed, and every inverse is verified to have succeeded.
- Never commit or persist mutated versions of the test or stale mutation backups.
- If verification environment is unstable (flaky), stop after 2-3 unstable runs. Flaky env is a `failed` outcome (so the queue stops cleanly) but with `cause: flaky-env` so triage knows it's environmental, not a test or product bug.

---

## The Index Regeneration Helper

Not a full skill, but a small utility used by `test-kb-bootstrap`, `test-brief`, and `test-implement`:

- Walks `kb/*.md`.
- Parses HTML-comment metadata blocks under each heading.
- Builds `kb/index.json`.
- Detects broken references: any `section_id` referenced in `kb-gaps.md` or `briefs/*.md` whose prefix matches a known kb file stem but doesn't resolve to a real section. Emits warnings to stderr (non-blocking).
- Detects duplicate section_ids across the kb. Emits warnings.
- Detects sections missing required metadata fields. Skips them with a warning.

The script is the **only** sanctioned mechanism for updating `kb/index.json`. Skills MUST invoke it after any kb mutation. **In-place JSON patching is not permitted** — it skips broken-reference detection and lets index drift accumulate silently.

Implemented as a standalone script the skills invoke, so it can also be run manually.

---

## Optional CLI Helper (`run-queue`)

A small CLI utility — **not a skill** — for batch processing. ~50–100 lines of Node or Python. Lives in the plugin under `scripts/run-queue` (or shipped separately). Optional: every case-by-case workflow works without it.

### Why a CLI tool, not a skill

Walking a queue and dispatching work is mechanical iteration, not reasoning. A skill would be a thin meta-layer over what is either natural agent behavior (when the user asks the agent to process the queue) or trivially scriptable (for headless batch runs). Keeping it as a CLI tool keeps the four skills focused on what skills are good at — guiding reasoning-heavy work — and gives users two clean modes with no overlap: case-by-case via skills, batch via the CLI.

### Behavior

1. Read `todo.json`.
2. Skip entries with status `verified`, `blocked`, `not_automatable`, `failed`.
3. For each remaining entry, in order:
   - `pending` → invoke `claude -p` with a prompt that triggers `test-brief` for this `case_id`.
   - `briefed` → invoke `claude -p` with a prompt that triggers `test-implement`.
   - `implemented` → invoke `claude -p` with a prompt that triggers `test-verify`.
4. After each invocation, re-read `todo.json` to pick up the status update written by the skill, then continue from the top (so a freshly `briefed` case can move on to `test-implement` in the same run).
5. Stop the loop on any case that becomes `blocked` or `failed` so a human can attend to it. Optionally support `--continue-on-block` for unattended overnight runs (still records each blocked/failed case in the final report).
6. Print a summary at the end: counts per status, time per case, list of cases needing attention.

### Sub-command: `run-queue init`

Scans a folder of test case markdown files and generates `todo.json` with one `pending` entry per file. Idempotent — running it a second time on the same folder adds only new cases and never overwrites existing entries.

### Constraints

- Must NOT do any reasoning of its own. It only reads status, picks a skill, shells out, and re-reads the queue.
- Must NOT silently retry failures. A failed `claude -p` invocation surfaces as a queue update (`failed`) by the skill itself; if the invocation crashes before updating the queue, the helper records the case as `failed` with a "harness crash" note and moves on (or stops, depending on flags).
- Must never write skill artifacts directly. All artifact writes are the skill's job.

---

## Universality Requirements (Re-emphasized)

Every skill, every prompt, every artifact template MUST avoid:

- References to specific languages (no "Python", "TypeScript", etc.).
- References to specific frameworks (no "Playwright", "Jest", "PyTest", etc.).
- References to specific domains (no "slot games", "e-commerce", "fintech", etc.).
- Assumptions that source code is accessible.
- Assumptions that the product is web-based (could be API, mobile, desktop, embedded).

All such specifics live in the kb of the specific project. The skills' instructions reference kb layers and sections, never concrete tools or domains.

When a skill needs to express something concrete in examples, it MUST mark these as illustrative and use diverse domains across examples (sometimes web, sometimes API, sometimes mobile) to reinforce the universality message.

---

## Open Decisions Deferred to Implementation

These were considered but deferred; implementer should follow the listed defaults:

- **Embeddings/vector index for semantic kb search** — defer. Start with tag/summary text search via `kb/index.json`. Revisit if text search proves insufficient at scale.
- **Parallel case processing** — defer. v1 is one case at a time.
- **History/analytics over kb evolution** — defer. `last_updated` per section is enough for now.
- **GUI for the workflow** — defer. Direct skill invocation (case-by-case) and the `run-queue` CLI helper (batch) are sufficient.

---

## Acceptance Criteria

The implementation is complete when:

1. All four skills exist as separate skill definitions with clear instructions.
2. Skills correctly read and update `todo.json` per the Queue Contract: `test-brief` transitions `pending` → `briefed` (or `blocked` / `not_automatable`), `test-implement` transitions `briefed` → `implemented` (or back to `pending` on inadequate brief), `test-verify` transitions `implemented` → `verified` (or `failed`). Each skill bails out cleanly when invoked on a case whose status doesn't match its stage. The optional `run-queue` CLI helper, given a folder of test cases, drives a full pending → verified pipeline and stops on `blocked` / `failed` for human attention.
3. Bootstrap can run on a project with no kb and produce a working scaffold; running it again on the same project does no harm.
4. The brief skill demonstrably refuses to ask questions whose answers exist in the kb or test case (test this with a contrived case).
5. The brief skill correctly handles all three gap-resolution paths.
6. Implement skill correctly returns control when a brief is found to be inadequate, rather than improvising.
7. Verify skill performs at minimum a lightweight mutation check on every test (including zero-assertion tests, which are flagged as smells), and a full mutation check with a verified-restoration manifest on tests in high-criticality areas per `risk-map.md`.
8. The kb-gaps file deduplicates correctly **within the same kind**: working through 5 cases that hit the same hard gap produces ONE entry with 5 `related_cases`. A hard gap and a soft gap on the same topic remain distinct entries.
9. Index regeneration produces a correct, parseable `kb/index.json` and surfaces broken references when sections are deleted. All skills regenerate via the script — no in-place patching.
10. `gap-resolution` and `manual` sections survive bootstrap re-runs unchanged.
11. Bounce-back paths preserve forensic state: `notes` is append-only, rejected briefs are renamed to `.rejected.md`, and entry-guard reconciliation handles crash residue without losing or duplicating work.
12. Skills work end-to-end on a sample project in at least two distinct domains (e.g., a web app and an API) without code changes — only kb content differs.

---

## Suggested Implementation Order

1. Define kb file format and metadata convention; write the index regeneration helper.
2. Implement `test-kb-bootstrap` — needed first because everything else reads kb.
3. Implement `test-brief` — the central skill. Get gap-resolution flow right here.
4. Implement `test-implement` — straightforward once brief format is solid.
5. Implement `test-verify` — last because it depends on all the above.
6. Define the `todo.json` schema and the Queue Contract; implement the optional `run-queue` CLI helper.
7. Run end-to-end validation on two projects of different domains.
