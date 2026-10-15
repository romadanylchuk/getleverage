---
name: code-map-update
description: Helper agent that keeps .openspec-worker/code-map.json in sync. Result mode refreshes the files listed in an implement/fix result; stale mode rescans files modified since the map was last updated (catches code changed by hand, e.g. via /opsx:apply). Spawned by /openspec-worker:run; not for direct use.
---

# Skill: code-map-update

> **Recommended model: Sonnet**

## Role
Keep `.openspec-worker/code-map.json` current. Not user-facing; exit silently.

## Hard scope rule
You MAY update entries in `.openspec-worker/code-map.json`. You MUST NOT modify source files, OpenSpec artifacts, or any other `.openspec-worker/` file.

## Modes (passed by the run)

### result mode — `result=<path>`
After `implement` or a fix. The path is one of:
- `.openspec-worker/runs/<id>/group-N-result.md` → `## What Was Implemented`
- `.openspec-worker/runs/<id>/fix-N-<iter>-result.md` or `fix-V-<iter>-result.md` → `## What Was Changed`

Collect the created/modified file paths listed there.

### stale mode — `mode=stale`
At the start of each run. Collect:
1. Files under the project root (honoring `profile.code_map.exclude`) whose modification time is later than the map's `last_updated`. Prefer `git` when available: files changed in `git diff --name-only` plus `git ls-files --others --exclude-standard`, plus files changed in commits since `last_updated` (`git log --since=<last_updated> --name-only --pretty=format:`).
2. Map entries whose file no longer exists → remove those entries.

If more than 200 files are stale, update the first 200 by most-recent change and log the remainder count in your final line (a rebuild via bootstrap may be better).

Set `last_changed_in` to `"manual"` for entries refreshed in stale mode.

## Schema

```json
{
  "version": 1,
  "last_updated": "<ISO timestamp>",
  "last_change": "<change id | manual>",
  "patterns": { "error_handling": "...", "naming": "...", "layout": "..." },
  "files": {
    "<relative path>": {
      "summary": "<one or two sentences>",
      "exports": ["<name>"],
      "role": "feature | utility | infra | config | test | type",
      "depends_on": ["<relative path>"],
      "last_changed_in": "<change id | manual>"
    }
  }
}
```

Entries hold summary, export **names**, role, depends_on, last_changed_in — never signatures, types, or code. The map is for navigation, not content.

## Process
1. Read the map and `profile.code_map.exclude`. Missing/unreadable map → exit without writing (report it in your final line).
2. For each collected file (skip excluded): read it (first ~5K chars is enough for the export surface) and set exports (top-level public names by language convention), summary (purpose, matching existing style), role, depends_on (project-internal imports only), `last_changed_in` (`current_change` from `run-context.json`, or `manual` in stale mode).
3. If the run passes `drift_files`, rescan those too.
4. Set `last_updated` = now, `last_change` = current change id or `manual`. Leave `patterns` unchanged unless a clear shift is visible.
5. Write the map; keep untouched entries verbatim.

## Rules
- Only changed / stale / drift entries are touched.
- Valid JSON, schema-compliant.
- Never delete the whole map.
