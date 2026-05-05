---
name: test-implement
description: Write the actual test code for a previously-briefed test case, following the brief precisely and reusing existing helpers and conventions from the project's kb. Make sure to use this skill whenever the user wants to "implement TC-XXXX", "write the test for this brief", "code up briefs/TC-XXXX.brief.md", "turn the brief into a real test file", or whenever a `briefed` entry in `todo.json` needs to move forward. Strict scope discipline — never invents helpers that already exist, never mutates the kb beyond appending a documented helper, and stops cold (returning the case to `pending`) the moment the brief turns out to be inadequate, rather than improvising.
---

# Skill: /test-suite:test-implement

> **Recommended model: Sonnet** for routine implementation. Reach for **Opus** only if the brief requires non-trivial new helper design or the test framework is unusual.

## Role

Translate one brief at `briefs/{case_id}.brief.md` into actual test code at the file location specified in the brief. Reuse existing helpers and follow project conventions from `kb/`. Update the queue when done.

This skill should feel mechanical when the brief is good. The reasoning work was done in `/test-suite:test-brief`; this skill is execution. If you find yourself making consequential decisions that aren't in the brief, that's a signal the brief is inadequate — see "When the brief is wrong" below.

## Inputs

- A brief at `briefs/{case_id}.brief.md` (or specified path).
- `kb/` — read-only except for one append rule (see "New helpers" below). Especially `kb/helpers.md`, `kb/patterns.md`, `kb/conventions.md`.
- The original test case file (referenced in the brief).
- Existing test files in the project — for stylistic and structural matching.

## Queue contract — entry guard

1. Resolve the `case_id` to its entry in `todo.json` and read `case_path` and `artifacts.brief`.

2. **Reconcile crash residue.** If `artifacts.test` is set or a test file exists at the path the brief specifies, but `status: briefed`, the previous run crashed between writing the test and updating the queue. Compute the SHA-256 of the existing test file, compare to a `.test-suite/last-write/{case_id}.sha256` sidecar if present:
   - If sidecars match: skip the implementation step, just update the queue (`status: implemented`) and exit. The previous run finished its content work.
   - If sidecars don't match or the sidecar is missing: refuse and ask the user. The disk has unverifiable state; overwriting risks destroying their edits.

3. **Verify status:**
   - `pending` — there's no brief; tell the user to run `/test-suite:test-brief` first.
   - `briefed` — proceed.
   - `implemented` / `verified` — already done. Refuse unless the user passed `--reimplement`. With `--reimplement`, archive the existing test to `<test-path>.{N}.bak` (next available N) before proceeding. With `--reimplement` against `verified`, refuse unless the user adds `--allow-downstream-invalidation`.
   - `blocked` / `not_automatable` / `failed` — needs human attention; refuse.

4. **Verify brief is well-formed:** the file at `artifacts.brief` exists AND contains every required section heading from the brief format (`# Brief:`, `## Criticality`, `## Intent`, `## Observable Points`, `## Determinism Notes`, `## Boundaries`, `## Implementation Outline`, `## Assumptions`, `## References`) AND each section has at least one non-blank line of content beyond the heading. If not, treat as "brief is wrong" — see below.

## Process

### 1. Read the brief in full

The brief is the source of truth for what to write. Read every section before touching code:
- **Criticality** — informs how rigorously you treat boundary checks (high-criticality tests demand stricter scope discipline).
- **Intent** — what assertions ultimately need to mean.
- **Observable Points** — what each assertion will check.
- **Determinism Notes** — where to place explicit waits, seeds, or mocks.
- **Boundaries** — what NOT to test (resist scope creep).
- **Implementation Outline** — the actual structure: file location, setup/teardown, step-by-step, assertions, any new helpers.
- **Assumptions** — note them; if any are clearly invalidated by the kb or existing tests, that's a "brief is wrong" trigger.
- **References** — the kb section_ids, existing tests, and related cases the brief leans on.

### 2. Cross-reference the kb

For every helper, pattern, and convention named in the brief by `section_id`, look it up in `kb/index.json` and read the actual section. The brief names *what* to use; the kb says *how* to use it.

If a referenced `section_id` doesn't resolve, the brief is stale (the kb has changed since the brief was written). Don't guess — see "When the brief is wrong".

If a referenced `section_id` resolves but the body has clearly changed since the brief was written (the brief says "use the X helper which takes (a, b)" but the kb section now describes a `(a, b, c)` signature), this is also a stale-brief signal. Bounce back.

### 3. Read 2-3 existing tests in the same area

Match style to the project, not to your priors. Look at:
- Naming — file names, test names, helper invocation idioms (whatever the project's runner uses — `describe/it`, `func TestX(t *testing.T)`, `class FooTests`, `def test_*`, `@Test`, `[Fact]`, etc.).
- File structure — imports, setup/teardown idioms, test grouping.
- Assertion style — which assertion library, message conventions.
- Determinism handling — what waiting/seeding patterns are actually used in this codebase.

If `kb/conventions.md` and the existing tests disagree, **the existing tests win for this implementation**, but **do not modify the kb**. Instead, append a divergence entry to `kb-drift.md` at the project root (create the file if missing) and continue:

```markdown
## <one-line summary of divergence>

<!--
drift_id: drift.{YYYY-MM-DD}.{slug}
discovered_during: TC-XXXX
kb_section: <section_id>
status: open
-->

**KB says:** <quote from the kb section>
**Existing tests do:** <observed pattern with one or two file paths as evidence>
**Resolved by this implementation:** <which one was followed and why>
```

The next `/test-suite:test-kb-bootstrap` run reads `kb-drift.md` and surfaces these in the bootstrap report so a human can resolve them — by editing the kb section to `source: manual` with the correct content, or by reconciling the codebase. **This skill never edits kb sections directly** (apart from appending a new helper, see below) — that contract belongs to bootstrap and to humans.

### 4. Resolve brief vs. conventions conflicts

If the brief's Implementation Outline names a file path that conflicts with `kb/conventions.md`, the brief wins (briefing is the layer where placement is decided). If the brief contradicts the *codebase's actual* placement convention as observed in §3, that's a "brief is wrong" trigger — bounce back with a description of the divergence.

### 5. Write the test

Follow the implementation outline step by step. Match the existing tests' style. Use only helpers that exist in `kb/helpers.md` or that the brief explicitly authorizes you to create.

Scope discipline:
- Do not add assertions the brief doesn't specify. Each assertion in your output must map back to an Observable Point in the brief.
- Do not add setup steps the brief doesn't call for.
- Do not refactor surrounding test files. If something is ugly nearby, leave it — that's a separate concern.

If the test file already exists at the brief's specified path (and the entry guard didn't catch it because it had no sidecar), refuse and ask the user before overwriting.

After writing, store a SHA-256 of the new test file at `.test-suite/last-write/{case_id}.sha256` (create the directory if missing). The sidecar lets the next run distinguish "we wrote that" from "the user edited it."

### 6. New helpers, if the brief authorized them

If the brief's Implementation Outline calls for a new helper or fixture:
- Place it where the project keeps such things (per §3 observations and `kb/conventions.md`).
- Match existing helper style and naming.
- Append a section to `kb/helpers.md` with the metadata block, `source: manual` (so future `/test-suite:test-kb-bootstrap` runs won't overwrite it). Include: when to use it, when not to use it, inputs/parameters expected (or "not applicable" for fixtures), and what the helper produces or affects.
- Regenerate `kb/index.json` by invoking `<plugin>/skills/test-kb-bootstrap/scripts/regen_index.py`. Do not patch the JSON in place — the patch path skips broken-reference detection.

If the brief did NOT authorize a new helper but you find yourself wanting one, consider first: is there an existing helper in `kb/helpers.md` that does the same thing? If yes, use it. If no existing helper covers it and the brief didn't authorize one, that's a "brief is wrong" trigger — bounce back. Don't introduce undocumented helpers.

If the brief authorized a new helper but you discover an existing helper that already covers the need, also bounce back — the brief author missed it. Note the existing `section_id` in your bounce-back message.

### 7. Sanity check before exiting

Before updating the queue:
- Does the test file exist at the path specified by the brief?
- Does every assertion map back to an Observable Point in the brief? Walk each assertion and tag it; if any can't be tagged, drop it (or bounce back if dropping breaks the test logic).
- Does the file's style match the 2-3 existing tests you sampled?
- If you added a helper, is it documented in `kb/helpers.md` with `source: manual` and is it in `kb/index.json`?
- Did you write a sidecar SHA at `.test-suite/last-write/{case_id}.sha256`?
- If `kb-drift.md` got an entry, did you note it in the queue notes for visibility?

## When the brief is wrong

The brief can be inadequate in several ways:
- A required section is missing or empty.
- A referenced `section_id` no longer exists in the kb (or has changed body since the brief was written).
- An Observable Point turns out to be unstable / non-existent / different in reality.
- The Implementation Outline references a helper that doesn't exist (and isn't authorized to be created).
- The Implementation Outline authorizes a new helper that already exists in the kb.
- An Assumption marked in the brief is clearly contradicted by the kb or existing tests.
- The Boundaries section omits something that comes up unavoidably during implementation.
- The brief's prescribed file location conflicts with the codebase's actual placement convention.

When you spot one of these, **stop writing.** Do not guess, do not silently expand scope, do not "fix" the brief mid-flight. Instead:

1. Discard any partial test file you've written (no sidecar SHA — there is no value in a half-written test).
2. Update `todo.json`: `status: pending`, **clear `artifacts.brief`** (the brief is no longer current), append a structured notes entry of the form `{stage: "implement", ts: "<ISO>", message: "Brief inadequate: <which section>: <what specifically>; suggested fix: <if any>"}`.
3. Move the brief to `briefs/{case_id}.brief.rejected.md` (overwriting any prior rejected brief). The next `/test-suite:test-brief` invocation will find the prior brief there and use it as context to avoid repeating the same mistakes — see the brief skill's "Re-brief context" handling.
4. Print a summary for the user: which brief section was inadequate, what specifically the problem is, what the user (or a re-run of `/test-suite:test-brief`) needs to address.
5. Exit.

The reason for this discipline: a test that was implemented "creatively" against a wrong brief is worse than no test at all — it gives false confidence. The cost of an extra round-trip through brief is small; the cost of a misleading test compounds across every change to the area it covers.

## Queue contract — exit transitions

Write the test file first (and its SHA sidecar), then update the queue with a temp-and-rename pattern.

| Outcome | `todo.json` mutation |
|---|---|
| Test written, sanity checks pass | `status: implemented`, `artifacts.test` filled in, append a `{stage: "implement", ts, message}` notes entry summarizing what was written and any drift recorded |
| Brief turned out to be inadequate | `status: pending`, **clear `artifacts.brief`**, append a notes entry describing the inadequacy |

`notes` is append-only across all skills. Never overwrite.

Never leave the queue claiming `implemented` if the test file isn't on disk.

## Interactive vs. non-interactive invocation

This skill must function under both:

- **Interactive** (a user is attached): on borderline calls (e.g., a divergence between kb and tests), you may briefly explain what you're doing and continue. The default behavior is non-blocking; do not pause for confirmation unless the action would overwrite user-authored content (existing test file with no sidecar match, archive of an `implemented` case under `--reimplement`).
- **Non-interactive** (e.g., spawned by `run-queue` via `claude -p`): never pause for input. Borderline calls follow the documented default. Anything that would have been a confirmation prompt becomes a refusal with an exit summary, so the queue stays consistent and a human can resume later.

## Universality

The skill is independent of language, framework, runner, or domain. Two consequences:

- Don't import test-framework idioms from elsewhere unless they appear in the existing tests or `kb/conventions.md`. The project's stack is whatever the project's stack is — JS, Python, Java, Go, Rust, Swift, Kotlin, Ruby, C#, F#, Scala, Elixir, embedded C, shell scripts, anything.
- Don't insert generic phrasing like "verify the user sees a success message" if the project has no users or no UI. Read the project's vocabulary (from `kb/product-spec.md` and existing tests) and use *its* terms — "the host", "the caller", "the device", "the consumer", whatever the kb says.

When examples are unavoidable in your reasoning notes, alternate domains (web UI, HTTP API, mobile, embedded firmware, CLI) so you don't drift toward any one stack.

## Critical constraints

- **Reuse over reinvention.** If `kb/helpers.md` lists a helper that does what you need, use it. Inventing parallel helpers fragments the codebase and creates two ways to do the same thing.
- **Conventions before personal preference.** When the project's existing patterns conflict with your priors, the project wins.
- **Scope minimum.** Implement exactly what the brief specifies. No more, no less.
- **Never mutate the kb beyond appending a documented helper section.** Drift goes to `kb-drift.md`; conflicts trigger bounce-back. Existing kb sections are read-only.
- **Stop on inadequacy.** Bouncing the case back to `pending` is the right move when the brief is wrong. Improvising is the wrong move.

## Outputs

- A test file at the location specified by the brief's Implementation Outline.
- Possibly new helper/fixture files, if the brief authorized them.
- Possibly a new section in `kb/helpers.md` (with `source: manual`) for any new helpers.
- Regenerated `kb/index.json` if a new helper was added.
- A SHA-256 sidecar at `.test-suite/last-write/{case_id}.sha256` for the test file.
- Possibly a new entry in `kb-drift.md` (kb/test divergence detected).
- `todo.json` updated per the queue contract above. `notes` is append-only.

## What this skill does NOT do

- Run the test it just wrote. That's `/test-suite:test-verify`.
- Modify the brief. The brief is read-only here (except for renaming to `.rejected.md` on bounce-back).
- Modify the kb beyond appending a `source: manual` helper section, when authorized by the brief.
- Refactor existing tests or production code.
- Resolve kb/test divergences in place. They go to `kb-drift.md` for human resolution.
