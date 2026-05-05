---
name: test-verify
description: Verify that an automated test (a) passes against the working product AND (b) actually catches regressions — by running it, then deliberately mutating the test or the observable surface to confirm it fails when it should. Make sure to use this skill whenever the user wants to "verify TC-XXXX", "make sure this test actually works", "check that the test catches breakage", "mutation-check this test", "run the implemented test", or whenever an `implemented` entry in `todo.json` needs to move forward. Distinguishes meaningful verification from sanity-checks: a passing test that asserts nothing useful is still a failure mode this skill catches.
---

# Skill: /test-suite:test-verify

> **Recommended model: Sonnet** for routine verification. Reach for **Opus** if mutation strategy needs careful design (e.g., a high-criticality test against a black-box product where the observable surface is hard to perturb).

## Role

Take one implemented test and verify two distinct things:

1. **It passes** against the working product.
2. **It fails** when the product (or its observable surface) is broken.

The second part is what separates real verification from a sanity check. A test that passes because it asserts nothing meaningful — for instance, a test that waits for an animation and then asserts on a property that's set unconditionally — will pass forever, including when the feature it claims to cover regresses. This skill is here to surface those tests and any others that look real but aren't.

## Inputs

- A test file produced by `/test-suite:test-implement` (path stored in `todo.json` at `artifacts.test`).
- The brief at `briefs/{case_id}.brief.md` — used for criticality determination (the brief's `## Criticality` section names the level and product areas explicitly).
- `kb/` — especially `kb/risk-map.md` (criticality lookup) and `kb/observable-surface.md` (what surface to perturb in mutation checks).

## Queue contract — entry guard

1. Resolve the `case_id` to its entry in `todo.json` and read `case_path`, `artifacts.test`, `artifacts.brief`.

2. **Verify status:**
   - `pending` / `briefed` — work isn't done yet; tell the user what stage to run.
   - `implemented` — proceed.
   - `verified` — already done. Refuse unless the user passed `--reverify` (e.g., the product changed and the user wants to re-validate). With `--reverify`, archive any prior verification report to `verify/{case_id}.verify.{N}.md` and proceed.
   - `blocked` / `not_automatable` / `failed` — needs human attention; refuse.

3. **Verify artifact integrity:** the test file at `artifacts.test` and the brief at `artifacts.brief` both exist. If either is missing, append a notes entry describing the missing artifact and refuse without changing status. (Don't bounce the case to `pending` — this is artifact integrity, not test inadequacy.) The user must investigate before progress can resume.

4. **Reconcile crash residue.** If `artifacts.verify` is set but the report is missing, or a mutation backup file exists at `.test-suite/mutation-backup/{case_id}.*`, the previous run crashed mid-mutation:
   - If a mutation backup exists, the test file may not be in its original state. Compare the current test file's SHA-256 to the sidecar at `.test-suite/last-write/{case_id}.sha256`. If they don't match, restore from the backup before proceeding. If the backup itself is corrupt or missing, refuse and flag for human intervention — do NOT proceed and risk verifying a tampered file.
   - Once integrity is restored, proceed.

## Process

### 1. Run the test

Run the test using the project's test runner (per `kb/conventions.md`). It must pass.

If `kb/conventions.md` doesn't supply a runnable command, refuse with a clear message and append a `kb-completeness` gap to `kb-gaps.md` so the team can fill it in. Do not guess a runner.

If it fails, diagnose which of three causes:

- **Flaky environment.** Re-running passes sometimes, fails other times, with no code changes. Don't retry indefinitely — that masks the issue. After 2-3 unstable runs, stop. Flaky env is not the test's fault, but per the queue contract it is still a `failed` outcome (so `run-queue` halts for human attention). Use the `notes` entry to tag the cause as `flaky-env` so triage can distinguish it from test or product bugs.
- **Actual product bug.** The test is correct, the product is wrong. Capture the failure details and report — this is a *good* outcome (the test caught a regression in its very first verification!), but the case is `failed` so a human can decide whether to file a bug, fix the product, or revise the test. Tag the notes entry as `product-bug`.
- **Test bug.** The test is wrong (incorrect assertion, wrong selector, mis-applied helper). Mark `failed` with notes tagged `test-bug` pointing at what looks broken about the test itself.

### 2. Lightweight mutation check (always)

Even if the test passed in step 1, run a lightweight check that the test isn't trivially permissive. This is the cheapest, highest-value safeguard against tests that pass because they assert nothing meaningful.

**Before any mutation:** copy the test file to `.test-suite/mutation-backup/{case_id}.{ts}.bak`. The integrity discipline (§"Critical constraints") depends on this.

**Identifying the headline assertion.** The "headline" assertion is the one that maps to the first Observable Point listed in the brief. If the brief lists multiple Observable Points, the headline is the assertion mapped to OP #1 in source order. If the test has zero assertions, the lightweight check is **not skippable** — record this as a smell ("test has no assertions") and downgrade verdict to `failed`. A passing test with no assertions is exactly the failure mode this step exists to catch.

Two micro-mutations, in order:

**Mutation A — change an expected value to something certainly incorrect.** Identify the most central expected value within the headline assertion. Change it to something obviously wrong (e.g., expected `42` → `999_999`; expected `"success"` → `"___SHOULD_FAIL___"`; expected `true` → `false`). Run the test. **It must fail.** If it still passes, the assertion isn't really exercising what it claims to.

**Mutation B — neutralize the headline assertion.** Replace the headline assertion with a no-op equivalent in the project's runner (commenting out, replacing with `assert true`, replacing with `pass`, whatever the language supports). Run the test. **It must fail or error** (because the test's purpose was that assertion). If it passes anyway, something else in the test is providing false confidence — flag this as a smell.

**For test types that don't fit cleanly:**
- **Negative test** (asserts an exception is thrown / an error is returned): Mutation A flips the expected error type/code to an obviously wrong one; Mutation B removes the act-step that triggers the error. Both must cause the test to fail.
- **Parameterized / data-driven test:** apply Mutation A and Mutation B to the headline assertion of the first row. Re-run only that row if the runner supports row-level filtering; otherwise re-run the whole test and verify the headline row fails.

**Restore the test to its original state after both mutations.** Use the backup at `.test-suite/mutation-backup/{case_id}.{ts}.bak`. After restore, recompute the SHA-256 and compare to the `.test-suite/last-write/{case_id}.sha256` sidecar. They must match exactly. If they don't, refuse to update the queue — surface "verification corrupted the test file, manual intervention required." This integrity check is non-negotiable.

If either mutation fails to make the test fail, that's a real finding: record it in the verification report as a smell with specific evidence, and downgrade the verdict from `verified` to `failed` (notes entry tagged `smell`).

### 3. Determine criticality

Read the `## Criticality` section of the brief — it has explicit `Level`, `Source`, and `Mapped product area(s)` fields populated by `/test-suite:test-brief`. No re-parsing of prose required.

If the brief was written before the criticality field was added (legacy brief from a prior schema), fall back to the two-source heuristic:
- **Primary:** explicit priority/severity tag in the test case file (in whatever metadata mechanism the case format supports).
- **Secondary:** match the brief's referenced product areas against `kb/risk-map.md` categories using a deterministic similarity metric (same metric as gap dedup in `/test-suite:test-brief`).

If the level can still not be determined, default to `medium` and append a `kb-completeness` gap to `kb-gaps.md`: "risk-map needs entry for {area}". Don't block verification on this — `medium` is a safe default — but surface it.

### 4. Full mutation check (high-criticality only)

For tests covering high-criticality areas, the lightweight check is not enough. Now perform a more rigorous check: deliberately break the *observable surface* the test depends on, and confirm the test catches it.

**Track every perturbation with an inverse.** Maintain a manifest in memory listing each perturbation and how to reverse it. After all perturbations are checked, walk the manifest in reverse order and execute every inverse. Verify each inverse succeeded (e.g., for a mock: confirm the original handler is restored; for a config edit: confirm the config matches a pre-perturbation snapshot; for a deployed-state change: confirm a probe returns the original state).

For each Observable Point in the brief, design a perturbation that should make the test fail:

- If the test verifies an event was emitted → simulate the event NOT being emitted (mock the emitter, intercept and drop, drop a hooked publisher — whatever `kb/patterns.md` supports for this surface). The test must fail.
- If the test verifies a state change → simulate the state NOT changing. The test must fail.
- If the test verifies an API response shape → return an empty / wrong-shape response. The test must fail.
- If the test verifies a side effect (file written, message published, hardware register set) → suppress the side effect path. The test must fail.

**If breaking the observable surface is impossible** (black-box product, no mocking infrastructure available, can't intercept the relevant signal), this is **a verification limitation, not a failure.** Record it clearly in the report as a structured limitation entry. The verdict is still `verified` — provided the lightweight check passed and step 1 passed — but the report flags exactly which Observable Points were not full-mutation-verified.

After all perturbations have been validated, **execute the inverse manifest and verify each restoration**. If any inverse fails to restore, the verdict is `failed` with notes tagged `restoration-failed` — leave-no-trace integrity is a hard requirement.

### 5. Write the verification report

Output at `verify/{case_id}.verify.md`:

```markdown
# Verification: {case_id}

<!-- machine-readable header
verdict: verified | failed
cause: pass | flaky-env | product-bug | test-bug | smell | restoration-failed | n/a
criticality: low | medium | high
generated_at: <ISO>
-->

## Verdict
verified | failed (with reason)

## Test run
- Result: pass | fail (cause: …) | flaky (n runs, pattern …)
- Duration: …
- Stack/runner: … (per kb/conventions.md)
- Output transcript: <path to captured stdout/stderr, optional>

## Lightweight mutation check
- Headline assertion: <description, mapped to Observable Point #1>
- Mutation A (wrong expected value): test failed as required | DID NOT FAIL — smell: …
- Mutation B (neutralized assertion): test failed as required | DID NOT FAIL — smell: …
- Test file restored: yes (sha matches sidecar)

## Criticality
- Level: low | medium | high
- Source: brief (#Criticality field) | case-tag fallback | risk-map heuristic | default-medium
- Areas: [<name>, ...]

## Full mutation check (only present if criticality is high)
- Observable Point 1: <description>
  - Perturbation: …
  - Result: test failed as required | could not perturb — limitation: …
  - Inverse executed: yes (verified) | inverse FAILED — see notes
- (repeat per Observable Point)
- Restoration manifest fully reversed: yes | NO — see Critical Issues

## Limitations
Anything that couldn't be verified, with reasons. Examples:
- Black-box product; could not perturb the `animationComplete` event directly.
- Test runner doesn't support per-test fixture overrides; mocked at the suite level only.
- High-criticality verification skipped because risk-map didn't have an entry for area "X" — kb-completeness gap recorded.

## Smells
Anything weird worth flagging even if not a hard failure.
```

### 6. Update the queue

Write the report first, then update the queue with a temp-and-rename pattern.

| Outcome | `todo.json` mutation |
|---|---|
| Test passed, lightweight check passed, full check (if applicable) passed | `status: verified`, fills `artifacts.verify`, append a `{stage: "verify", ts, message, cause: "pass"}` notes entry |
| Test failed (product bug, test bug, or flaky env) | `status: failed`, fills `artifacts.verify`, append a notes entry tagged with the cause |
| Test passed but mutation checks revealed smells | `status: failed`, fills `artifacts.verify`, append a notes entry tagged `smell` with evidence |
| Restoration failed (test file or surface couldn't be cleanly reverted) | `status: failed`, fills `artifacts.verify`, append a notes entry tagged `restoration-failed`. Surface this loudly — it's an environmental hazard. |

`notes` is append-only across all skills. Never overwrite.

## Critical constraints

- **The test file on disk after this skill exits must match the SHA-256 sidecar at `.test-suite/last-write/{case_id}.sha256` byte-for-byte.** If it doesn't, the queue is not updated to a successful state. Use the mutation backup at `.test-suite/mutation-backup/{case_id}.{ts}.bak` to restore. After restore, verify, then delete the backup.
- **Every observable-surface perturbation in step 4 has an explicit inverse, and every inverse is executed and verified.** Mocks, intercepts, deployed-state changes, fixture overrides — all must be reversed and confirmed reversed. A residual mock in another test's session is a foot-gun.
- **Never commit or persist mutated versions of the test.** A `verify/` directory checked into source control with mutated copies, or a `.test-suite/mutation-backup/` directory with stale backups, is a bug. Delete backups after successful restoration.
- **Don't retry flaky tests indefinitely.** Flakiness is a finding worth surfacing, not a problem to mask. After 2-3 unstable runs with no code change, stop and report.
- **A passing test that doesn't catch breakage is a failure.** This is the central insight of this skill — verifying that a test fails when the product is broken is just as important as verifying it passes when the product works.

## Universality

This skill is independent of language, framework, runner, or domain. The mutation strategies above are described in observable-surface terms (events, state, API responses, side effects) precisely because they generalize across web, mobile, API, embedded, CLI, etc. The specific *mechanics* of each mutation come from `kb/patterns.md` and `kb/conventions.md` — read them, don't invent.

When perturbing observable surface in a black-box product, the available mechanisms are narrower (often: only what the deployed surface itself exposes). That's why the skill treats "could not perturb" as a recorded limitation, not a failure — a black-box product with limited harness shouldn't be punished for being black-box.

The integrity discipline (sidecar SHA, mutation backups) does not assume git or any specific VCS. Any project can compute a SHA-256; any filesystem can hold backups. If the project does have git, the user is welcome to layer additional safety (a `git stash` before mutation, a `git status` check after restore) — but the skill doesn't require it.

## Outputs

- `verify/{case_id}.verify.md` — the verification report.
- `todo.json` updated per the queue contract above. `notes` is append-only. `artifacts.verify` filled.
- Possibly a `kb-completeness` gap in `kb-gaps.md` (when criticality couldn't be determined and `risk-map.md` needs entries, or when `kb/conventions.md` lacks a runner command).
- The test file unchanged (verified via SHA sidecar). The product unchanged. The observable surface unchanged (all perturbations reversed).

## What this skill does NOT do

- Fix the test when verification reveals issues. That's a human decision (or a re-run of `/test-suite:test-implement` after the brief is revised).
- Fix the product when verification reveals a real bug. That's outside the test-suite plugin's scope.
- Mark a test "verified" without running both the pass case and the lightweight mutation check (and the full mutation check, if criticality is high).
- Persist any mutation of the test file or the observable surface beyond the run.
- Edit kb sections directly. Soft gaps and kb-completeness gaps are recorded in `kb-gaps.md`; resolution of those gaps is the job of bootstrap and brief.
