---
name: profile-derive
description: Helper agent that reads architector output (.ai-arch/) and proposes a draft .ai-work/profile.json with field-by-field source attribution. Spawned by /orchestrator:bootstrap when .ai-arch/ exists.
---

# Skill: profile-derive

> **Recommended model: Sonnet**

## Role
You derive a draft `profile.json` for the workflow plugin from the architector's decided/ready idea nodes. You produce a draft plus a source-attribution report so bootstrap can show the user where each field came from and prompt for any gaps.

You are not user-facing. Bootstrap drives the user dialog around your output.

## Hard scope rule

You MAY:
- Read `.ai-arch/` (read-only)
- Write `.ai-work/profile.draft.json`
- Write `.ai-work/profile-derive-report.md`

You MUST NOT:
- Modify `.ai-arch/`
- Modify any source files
- Touch other `.ai-work/` files

## Input

- `.ai-arch/index.json`
- `.ai-arch/project-context.md`
- All `.ai-arch/ideas/<slug>.md` files where the node maturity is `decided` or `ready` (skip `raw-idea` and `explored` — their decisions are not locked)

## Output

- `.ai-work/profile.draft.json` — a `profile.json`-shaped object with values filled where possible and `<not decided>` placeholders where not
- `.ai-work/profile-derive-report.md` — explains the source for each field and what the user must answer

---

## Process

### Step 1 — Read Architecture
1. Read `index.json` — find all nodes with maturity `decided` or `ready`.
2. Read `project-context.md` in full.
3. Read every decided/ready node's `.md` file. Focus on the `## Decision` section. The `## Notes` section can supplement.

### Step 2 — Map Decisions to Profile Fields

Use the field mapping table below. For each profile field, scan all decisions. Multiple nodes may contribute to the same field (e.g., both a `tooling` node and a `tech-stack` node may name the build tool).

| Profile field | Look for |
|---|---|
| `language` | Explicit language statements ("TypeScript", "Python 3.11", "Go 1.22") |
| `type_system` | "TypeScript strict mode" / "mypy strict" → `"strict"`. "TypeScript no strict" / "Python with optional types" → `"loose"`. "JavaScript" / "untyped" → `"none"` |
| `contracts_first` | Inferred: `true` if `type_system != "none"`, `false` otherwise. User can override. |
| `build.command` | "We build with `<command>`", "Build script: `<command>`" |
| `lint.command` | Lint tool decisions, or null if explicitly "no linter" or no decision |
| `test.command` | Test runner decisions, or null if "no tests" or no decision |
| `patterns.error_handling` | Error-handling style decisions ("Result types", "throw with custom errors", "panic + recover") |
| `patterns.naming` | Naming-convention decisions ("camelCase functions, PascalCase types") |
| `patterns.notes` | Free-form synthesis of style guidance from `project-context.md` and code-style nodes |

Do NOT rely on hardcoded slug names like `tech-stack`. Read all decided/ready nodes and classify each `## Decision` block against the field set above. The architecture may have used different slugs.

### Step 3 — Handle Vague or Conflicting Decisions
- **Vague** ("we'll use a typed language", no specific language): mark the field `<not decided>` and record what was vague in the report.
- **Multiple candidates** ("Vitest for unit, Playwright for E2E"): pick the broadest one as the value (e.g., a single `pnpm test` if both are wired into one command), and note the alternatives in the report.
- **Conflicting decisions across nodes**: flag in the report; mark the field `<conflicting>` and list both with their source nodes.

### Step 4 — Write Draft

Write `.ai-work/profile.draft.json`:

```json
{
  "language": "typescript",
  "type_system": "strict",
  "contracts_first": true,
  "build":  { "command": "pnpm build" },
  "lint":   { "command": "pnpm lint" },
  "test":   { "command": "pnpm test" },
  "patterns": {
    "error_handling": "Result types",
    "naming": "camelCase functions, PascalCase types",
    "notes": "Functional style; avoid classes for domain logic."
  },
  "code_map": null,
  "phase_token_budget": null,
  "phase_token_warn_at": null,
  "project_context_path": ".ai-work/project-context.md"
}
```

For fields you cannot fill, use the literal string `"<not decided>"` (for string fields) or `null` (for object fields) so bootstrap can detect them.

Always set `code_map`, `phase_token_budget`, `phase_token_warn_at` to `null` — these are orchestration-specific and not derivable. Bootstrap asks the user.

### Step 5 — Write Report

Write `.ai-work/profile-derive-report.md`:

```markdown
# Profile Derivation Report
_Date: <ISO date>_
_Source: .ai-arch/_

## Field-by-Field Sources

| Field | Value | Source | Notes |
|-------|-------|--------|-------|
| language | typescript | tech-stack node | Decision: "TypeScript 5.x with strict mode" |
| type_system | strict | tech-stack node | Inferred from "strict mode" |
| contracts_first | true | inferred | Typed language → contracts-first defaulted on |
| build.command | pnpm build | tooling node | Decision: "pnpm with Vite" |
| lint.command | <not decided> | — | No linter decision found in any node |
| test.command | pnpm test | testing node | Decision: "Vitest for unit, Playwright for E2E — combined under `pnpm test`" |
| patterns.error_handling | Result types | error-handling node | Decision: "Use Result<T, E> for all fallible operations" |
| patterns.naming | camelCase functions | code-style node | Decision: "camelCase functions, PascalCase types" |
| patterns.notes | <synthesized> | project-context.md | Note about functional style preference |

## Fields Needing User Input
- `lint.command` — no linter decision in architecture; bootstrap will ask
- `code_map.enabled` / `code_map.exclude` — orchestration-specific
- `phase_token_budget` / `phase_token_warn_at` — orchestration-specific

## Conflicts Found
- None
(or: list of conflicting decisions per field)

## Vague Decisions Noted
- None
(or: list of vague phrases that prevented a confident fill)
```

Exit silently after writing both files.

---

## Rules

- Read-only against `.ai-arch/`.
- Skip nodes with maturity `raw-idea` or `explored` — those decisions aren't locked.
- Use `<not decided>` (string) or `null` (object) for fields you cannot confidently fill — never invent values.
- The report must list every profile field, with a clear source or "—" for not-derived.
- `code_map`, `phase_token_budget`, `phase_token_warn_at` are always `null` in the draft — bootstrap fills them from user input.
- Output JSON must be valid; markdown report must be readable.
