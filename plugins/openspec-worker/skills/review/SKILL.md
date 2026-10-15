---
name: review
description: Code reviewer for openspec-worker. Evaluates the code quality of one implemented task group (or the whole change) against the project's patterns and the change's design decisions. Spawned by /openspec-worker:run; not for direct use.
---

# Skill: /openspec-worker:review

> **Recommended model: Sonnet**

## Role
Evaluate **code quality** — not whether the plan was followed (the implement verifier did that) and not spec coverage (verify does that).

## Invocation
```
/openspec-worker:review group-N
/openspec-worker:review all
```

## Preconditions
`.openspec-worker/run-context.json` → `<id>`.

## Input
- `.openspec-worker/runs/<id>/group-N-result.md` (or all group results for `all`) and any `fix-N-*-result.md`
- `openspec/changes/<id>/design.md` (if present) — decisions the code must respect
- `.openspec-worker/runs/<id>/plan-notes.md`
- `.openspec-worker/profile.json`, `code-map.json` (to find unchanged neighbors)
- Every changed source file, in full; 1–2 unchanged neighbors from the same module for style

## Checklist

### Correctness
- [ ] Unhandled error cases?
- [ ] Runtime assumptions that can fail (null access, bounds, async races)?
- [ ] Magic numbers / hardcoded values that should be constants or config?
- [ ] Actual-file reads cited in the result for every modified or depended-on file?

### Design conformance
- [ ] Code follows the Decisions in `design.md` (no silently chosen alternative)?

### Consistency (`profile.patterns`)
- [ ] Error handling pattern, naming, module structure match the codebase?
- [ ] Existing helpers reused instead of reimplemented?

### Clarity
- [ ] Self-explanatory names; single-purpose functions; no duplicated logic; complex conditions named/explained?

### Types — skip if `profile.type_system == "none"`
- [ ] Escape-hatch types replaceable with proper ones? Missing return types on public functions? Overly broad generics?

### Tests — skip if `profile.test == null`
- [ ] Happy path and main edge cases covered? Tests assert behavior, not implementation? Obvious regression cases missing?

## Severity
- **Must fix** — causes bugs, violates design decisions or project contracts, loose types on critical paths. (Triggers the fix loop.)
- **Should fix** — inconsistency/duplication/clarity that will grow. (Picked up by verify's fix loop if still present.)
- **Suggestion** — optional.

A pattern that looks wrong but is consistent with the rest of the codebase is a Suggestion at most.

## Output
`.openspec-worker/runs/<id>/review-N-report.md` (or `review-all-report.md`):

```markdown
# Review Report: <id> group N | all
_Date: YYYY-MM-DD_

## Status: PASSED | HAS_ISSUES

## Must Fix
- **file:line** issue → concrete suggestion

## Should Fix
- **file:line** issue → concrete suggestion

## Suggestions
- **file:line** ... → ...

## Summary
2–3 sentences.
```

## Rules
- Every issue has a concrete suggestion.
- No architectural changes beyond the change's scope.
- Don't modify any file except the report.
