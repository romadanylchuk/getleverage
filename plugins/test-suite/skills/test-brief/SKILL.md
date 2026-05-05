---
name: test-brief
description: Analyze a single test case and produce a combined brief + implementation plan as one markdown artifact, surfacing knowledge gaps to the user with three resolution paths (answer now, mark the case blocked, or allow an explicit assumption). Make sure to use this skill whenever the user wants to "brief a test case", "plan how to automate TC-XXXX", "analyze this test case", "produce an implementation outline for a test", "figure out what this test really needs", or whenever a `pending` entry in `todo.json` needs to move forward. The skill enforces pre-question discipline — it refuses to ask questions whose answers are already in the kb or the test case — so it will not waste the user's time on lookup-shaped questions.
---

# Skill: /test-suite:test-brief

> **Recommended model: Opus.** This is the central reasoning skill of the test-suite — its analysis quality determines the quality of everything downstream. Don't downgrade.

## Role

Take one test case and produce a combined **brief + implementation plan** as one markdown artifact at `briefs/{case_id}.brief.md`. Surface knowledge gaps to the user *immediately, at the point of discovery*, with three resolution paths. Update the queue when done.

This is the central skill of the suite. Get it right and `/test-suite:test-implement` becomes mechanical. Get it wrong (assume away gaps, ask shallow questions, miss intent) and the implementation will reflect that — flaky, scope-creeping, or testing the wrong thing.

## Inputs

The skill accepts either:
- A path to a test case file (manual, ad-hoc invocation), or
- A `case_id` that maps to an entry in `todo.json` (queue-driven invocation).

If invoked with a path, derive `case_id` from the filename: strip the extension and any leading directory components (e.g., `test-cases/TC-1234.md` → `TC-1234`). Reject filenames whose stem contains characters outside `[A-Za-z0-9._-]`.

It also reads (read-only for analysis, writable on gap resolution):
- `kb/` — every layer, plus `kb/index.json` for fast lookup.
- `kb-gaps.md` — the persistent gap log. If absent, the skill creates it on first gap write.
- Existing test files in the project — used as stylistic and structural reference for the implementation outline.
- Linked or related test cases, when the case file references them.

## Queue contract — entry guard

Before doing anything else:

1. **Resolve the case in `todo.json`:**
   - If `todo.json` doesn't exist and the user supplied a case path, create it with one entry for this case (`status: pending`, `case_path` set).
   - If `todo.json` exists but the case isn't listed and the user supplied a path, append a new entry (`status: pending`, `case_path` set).
   - If `todo.json` exists and the case is listed, read `case_path` and `artifacts` from the entry.
   - If invoked with a `case_id` and the case isn't listed, refuse with a clear message — invent nothing.

2. **Reconcile crash residue.** Before checking status, look for orphan artifacts:
   - If `artifacts.brief` is set or `briefs/{case_id}.brief.md` exists on disk but `status: pending`, the previous run crashed between writing the brief and updating the queue. Delete the stale brief file (and clear `artifacts.brief`) before proceeding — the analysis will be re-done.
   - If the user wants to inspect the orphan first, they can pass `--keep-orphan`; then refuse to proceed and exit.

3. **Verify status.**
   - `pending` — proceed.
   - `briefed` / `implemented` / `verified` — work is done. Refuse unless the user explicitly passed `--rebrief`. With `--rebrief`, archive the existing brief to `briefs/{case_id}.brief.{N}.md` (next available N) and reset status to `pending` before proceeding. With `--rebrief` against `implemented` or `verified`, also refuse unless the user adds `--allow-downstream-invalidation`, since the test and any verification report will be invalidated.
   - `blocked` — refuse. The lifecycle "answer gap → return related cases to pending" is what unblocks cases. If the case is still in `blocked`, the gap is still open. Tell the user which gap is blocking and exit.
   - `not_automatable` / `failed` — refuse; needs human review.

Bailing out on a status mismatch is not a refusal — it's protecting downstream work from getting half-rewritten artifacts.

## The four analytical layers

For each layer, **first** attempt to find the answer in available artifacts (kb, case file, existing tests, code). Only when an answer cannot be reasonably extracted does a gap surface.

### Layer 1 — Intent

What is this test case *really* verifying? What breaks for users (or callers, or the system, depending on what kind of product this is) if this functionality is broken? The literal scenario described in the case is the surface; intent is what makes assertions meaningful.

Pull from:
- `kb/product-spec.md` — for product vocabulary and business logic.
- The case text — including any priority/severity tag in whatever metadata mechanism the case format supports (YAML front-matter, an explicit `Priority:` line, a ticket field).
- Related cases the file links to — they often share intent context.
- `kb/risk-map.md` — to check whether this functionality is high-criticality (matters for `/test-suite:test-verify` later, and informs how strict the brief should be).

A test that "verifies the login form" is shallow. A test whose intent is "verify that legitimate users can authenticate within 2 attempts and that brute-force protection kicks in on the third" is precise. (Same principle for an API endpoint, a mobile flow, or a firmware command — the "intent" is whatever guarantee the product makes to its consumers.)

### Layer 2 — Observable surface

What can be observed externally to verify the intent? Which events, API responses, UI affordances, state values, log entries, network signals are available? For each candidate observable, is it:
- **Stable** — unlikely to change with refactors?
- **Deterministic** — does it fire reliably, the same way, every run?
- **Direct** — does it actually evidence the intent, or is it a proxy that could pass while the real thing is broken?

Pull from:
- `kb/observable-surface.md` — the highest-value layer for this question.
- Existing tests in adjacent areas — they show what is *currently* observed (and sometimes, painfully, what is observed badly).
- Source code or API specs (if accessible).

Prefer the most direct observable available. A test that asserts on a "loading indicator gone" is a proxy; a test that asserts on the underlying API response, or on a state-transition log entry, is closer to the truth.

### Layer 3 — Determinism

Where in the scenario are non-deterministic elements (animations, RNG, network, race conditions, time-dependent behavior)? What does `kb/patterns.md` say about handling each? Where will explicit waits, seeds, or mocks be needed?

Flag every async or stochastic boundary. For each, name the pattern from `kb/patterns.md` you'll apply. If the kb has multiple candidate patterns, pick the one whose preconditions match this case and document the choice. If no pattern matches — that's a gap.

### Layer 4 — Boundaries

What is this test deliberately NOT verifying? What's already covered by sibling tests? What edge cases are out of scope?

Without explicit boundaries, tests sprawl: they accumulate assertions until they become fragile, slow, and hard to interpret when they fail. The brief must say what's *out of scope*, not just what's in.

If Layer 4 reveals that a sibling test already covers this case fully, do not produce a brief. Update `todo.json` to `not_automatable` with a `notes` entry of kind `redundant`, naming the existing test path. (The state machine has no `redundant` status; folding into `not_automatable` keeps the enum small.)

Pull from:
- Case text (often has explicit "out of scope" notes).
- Adjacent test files for the same functional area.
- Related cases that handle adjacent scenarios.

## Pre-question discipline

Before asking the user **any** question, demonstrate you have done the work. The single most damaging failure mode of a brief skill is asking lookup-shaped questions that the user has to translate back into "did you check the kb?".

Required search checklist before *every* question:
1. Searched the relevant kb layer (use `kb/index.json` for efficiency — query by tag and summary).
2. Searched existing tests for similar scenarios (grep on the area, the function names mentioned, similar assertion patterns). If there are no existing tests yet (greenfield project), record that fact and skip this step.
3. Examined source code or API specs if accessible.
4. Re-read the test case and any cases it links to. If a linked case path doesn't resolve (typo, deleted file), record the broken link in `kb-gaps.md` as a `kb-completeness` gap and proceed without it.

When a question is genuinely warranted, frame it with:
- **The specific question**, narrowly scoped.
- **A summary of what was already searched and found.**
- **Why the search was insufficient.**

Bad question:
> How do I check that the auth flow succeeded?

Good question (web example):
> I need to verify the user is authenticated after the auth flow completes. I checked `kb/observable-surface.md` (no auth-related entries), existing tests in `tests/auth/` (they use a `loginAsUser` helper but don't verify the resulting state explicitly), and source code is not accessible in this project. Is there a deterministic signal — a session cookie, a stored token, a UI affordance — that indicates authenticated state, or should the test rely on attempting an authenticated action and asserting it succeeds?

Good question (API example):
> The case asserts that a `POST /orders` succeeds. I checked `kb/observable-surface.md` (entries for `200 OK` shape but no entry on idempotency-key handling), `tests/orders/` (existing tests assert on response body but not headers), and the OpenAPI spec (says `Idempotency-Key` header is "supported" but doesn't define which response indicates it took effect). Is the idempotency response signaled in a header, in the response body, or only by the absence of duplicate side effects?

The good questions show the user that the gap is real, scope the answer, and give them the option to redirect.

## Gap resolution — three paths

When a real gap surfaces, follow these steps in order:

### Step A — Match against existing gaps (before path divergence)

Scan `kb-gaps.md` for any `open` gap with overlapping subject. Match heuristic:
- Same `layer`, AND
- ≥1 tag in common, AND
- Question text similarity above a sensible threshold (e.g., trigram or BM25 on normalized text — pick a deterministic metric the implementer can reproduce; document it in your search notes).

Match results:
- **Match found**: this is a re-encounter. Hold the existing `gap_id` for use by the chosen resolution path.
- **No match**: this is a new gap. Hold the candidate `gap_id` (`gap.{YYYY-MM-DD}.{slug-of-question}`) and a `kind` (default `hard`).

### Step B — Present the question and offer three paths

Do **not** offer a fourth "skip silently" option — that's how briefs become assumption soup that breaks at implement time.

#### Path 1 — Answer directly

The user supplies the answer.

1. Continue the brief using the answer.
2. Write the answer as a new section in the appropriate `kb/<layer>.md` file with `source: gap-resolution`, today's `last_updated`, and `section_id: <file-stem>.<slug-of-title>`. Compute a body hash if the section format includes one.
3. Regenerate `kb/index.json` by invoking `<plugin>/skills/test-kb-bootstrap/scripts/regen_index.py`. (Do not patch the JSON in place — the patch path skips broken-reference detection.)
4. Update the gap log:
   - If Step A found a match: mark the existing entry `status: answered`, fill `resolution` (the user's answer summarized) and `resolved_into` (the new section's `section_id`). Then return any other cases in `related_cases` from `blocked` back to `pending` in `todo.json` — the answer may have unblocked them too.
   - If Step A found no match: do NOT create a new gap entry. The question was asked, answered, and recorded into kb in one session. The audit trail is the new kb section's `source: gap-resolution` marker plus `last_updated`.

#### Path 2 — Mark blocked

The user can't answer right now (needs to ask someone, doesn't know yet, isn't a decision they own).

1. Record the gap in `kb-gaps.md`:
   - If Step A found a match: append the current `case_id` to the existing entry's `related_cases`. Do not duplicate.
   - If Step A found no match: create a new entry with `kind: hard`, `status: open`, `related_cases: [<case_id>]`, and the searched-and-found summary from pre-question discipline.
2. Update the case in `todo.json`: `status: blocked`, `blockers: [<gap_id>]`.
3. Stop processing this case. Print a clear summary: which gap is blocking, who might know, what artifacts you searched.

#### Path 3 — Allow assumption

The user wants you to proceed with an explicit assumption (often used for low-risk gaps, or when the answer is "probably X but verify it").

1. Continue the brief, but mark the assumption clearly in the artifact under `## Assumptions` with the form: "ASSUMPTION: <what was assumed> — would be invalidated if <condition>".
2. Record a soft entry in `kb-gaps.md`:
   - If Step A found a match and it was already `kind: soft`: append the current `case_id` to `related_cases`.
   - If Step A found a match and it was `kind: hard`: do NOT silently merge — add the current `case_id` to `related_cases` but raise the entry's `kind` to `hard` (a hard gap shouldn't be downgraded by another case's assumption). The assumption stands for this brief; the gap remains hard for the rest.
   - If Step A found no match: create a new entry with `kind: soft`, `status: open`, `related_cases: [<case_id>]`, and a note "proceeded under assumption in brief {case_id}".
3. Proceed with the brief.

### Gap entry format

```markdown
## How to detect win animation completion

<!--
gap_id: gap.2026-05-05.win-animation-completion
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

`kind` values:
- `hard` — blocks at least one case until answered.
- `soft` — at least one case proceeded under assumption; answer would validate or invalidate that assumption.
- `kb-completeness` — meta-gap: the kb itself is missing structure (e.g., risk-map has no entry for an area, a related case file is broken). Recorded for the team to address; does not block individual cases.

`status` values: `open`, `answered`, `wont-fix`. Independent of `kind`.

Dedup respects `kind`: a hard gap and a soft gap on the same topic are distinct entries.

## Brief artifact format

Output the brief at `briefs/{case_id}.brief.md` with this exact structure:

```markdown
# Brief: {case_id} — {short title}

## Criticality
- Level: low | medium | high
- Source: explicit case-tag | risk-map heuristic | default
- Mapped product area(s): [<name>, ...]   ← named so /test-suite:test-verify can match against risk-map without re-parsing prose

## Intent
What this test really verifies. Why it matters.

## Observable Points
The specific signals this test will use, with references to kb section_ids. For each, note stability and determinism.

## Determinism Notes
Non-deterministic elements and how they will be handled. Reference patterns from kb/patterns.md by section_id.

## Boundaries
What this test does NOT cover. Related tests/cases that handle adjacent scenarios.

## Implementation Outline
- File location and naming (per kb/conventions.md).
- Setup/teardown approach (referencing existing helpers from kb/helpers.md by section_id).
- Step-by-step structure of the test.
- Specific assertions and their justifications — each assertion should map back to an Observable Point above.
- Any new helpers/fixtures that need to be created (with rationale).

## Assumptions
Explicit list of assumptions made during analysis (from "allow assumption" gap responses). Each tagged with what would invalidate it.

## References
- Test case: {path}
- KB sections used: [section_id, ...]
- Existing tests referenced for style: [paths]
- Related cases: [case_ids]
- Re-brief context: {N-th brief; previous brief at briefs/{case_id}.brief.{N-1}.md; previous bounce-back reason summarized}   ← present only when --rebrief was used
```

The structure is rigid because `/test-suite:test-implement` reads it. A missing required section will trigger a brief-inadequate bounce-back.

## Not-automatable detection

If, after the four-layer analysis, the case genuinely cannot be automated — requires real hardware, manual visual judgment, physical button press, real video stream, real RF input, etc. — do **not** produce a brief. Instead:

1. Update `todo.json`: `status: not_automatable`. Append to `notes` an entry of the form `{stage: "brief", ts: "<ISO>", message: "Not automatable: <reason>; what would change this: <condition>"}`.
2. Print a summary explaining why and what *would* make it automatable.

Producing a half-baked brief for an unautomatable case is worse than refusing — it sends downstream skills chasing a goal that can't be reached.

## Queue contract — exit transitions

Write artifact first, then update the queue. Use a temp-and-rename pattern for the queue write so a partial write can't corrupt `todo.json`. The entry-guard reconciliation step (above) handles the case where the artifact is on disk but the queue update never happened.

| Outcome | `todo.json` mutation |
|---|---|
| Brief produced | `status: briefed`, fills `artifacts.brief` with the brief path, appends a notes entry `{stage: "brief", ts, message}` summarizing what was decided |
| Gap blocking, user picked path 2 | `status: blocked`, `blockers: [<gap_id>]`, appends a notes entry naming the gap |
| Case is genuinely not automatable | `status: not_automatable`, appends a notes entry with the reason |

`notes` is an array of structured entries. **Append, never overwrite.** Each entry: `{stage, ts, message}`. The forensic record across stage transitions matters — overwriting destroys it.

Never leave the queue claiming `briefed` if `briefs/{case_id}.brief.md` isn't on disk.

## Universality

This skill must work for any project regardless of language, framework, or domain. Avoid assumptions like "the product is a web app", "tests are in JavaScript", "there is a UI". The kb is the source of truth for domain and stack details — read it; don't import knowledge from elsewhere.

When generating the brief's prose, use the project's vocabulary (extracted from `kb/product-spec.md`) rather than generic test-automation phrasing. A brief that talks about "the user" when the project's vocabulary is "the trader" reads as foreign and signals shallow analysis. Same for API products ("the caller"), embedded ("the host"), CLI tools ("the invoker").

## Outputs

- `briefs/{case_id}.brief.md` — the brief artifact (on the success path).
- Mutations to `todo.json` per the queue contract above. `notes` is append-only.
- Mutations to `kb/<layer>.md` and `kb/index.json` if any gaps were resolved (path 1).
- Mutations to `kb-gaps.md` if any gaps were recorded (paths 2 and 3) or matched (all paths).

## What this skill does NOT do

- Write test code. That's `/test-suite:test-implement`.
- Run tests. That's `/test-suite:test-verify`.
- Re-bootstrap the kb from sources. That's `/test-suite:test-kb-bootstrap`.
- Pick the next case from the queue. The caller picks; this skill processes.
- Modify or delete sections marked `source: manual` or `source: gap-resolution`. Those are immutable.
