# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**getleverage** is a Claude Code plugin marketplace. It catalogs and hosts plugins that extend Claude Code with new skills, workflows, and integrations. Each plugin lives in its own directory under `plugins/` and is independently installable.

## Repository Structure

```
.claude-plugin/
  marketplace.json          ← marketplace manifest (lists all plugins)
plugins/
  architector/              ← first plugin
    .claude-plugin/
      plugin.json           ← plugin manifest
    skills/
      init/SKILL.md
      explore/SKILL.md
      map/SKILL.md
      decide/SKILL.md
      status/SKILL.md
      finalize/SKILL.md
    README.md               ← plugin-specific documentation
```

## Adding a New Plugin

1. Create `plugins/<name>/` with:
   - `.claude-plugin/plugin.json` — plugin manifest (name, version, description, author, keywords)
   - `skills/<skill-name>/SKILL.md` — one file per skill (YAML frontmatter + skill definition)
   - `README.md` — plugin documentation
2. Add an entry to `.claude-plugin/marketplace.json` in the `plugins` array
3. Each plugin entry needs: `name`, `description`, `category`, `source` (path like `./plugins/<name>`)

## Plugin Conventions

- **Naming:** lowercase, hyphenated (e.g., `my-plugin`)
- **Categories:** `development`, `productivity`, `deployment`, `database`, `monitoring`, `security`, `design`, `learning`
- **Skills:** each skill is self-contained in a single `SKILL.md` with YAML frontmatter (`name`, `description`)
- **Separation of concerns:** skills within a plugin should have distinct, non-overlapping responsibilities

## Existing Plugins

### architector

Multi-session architecture exploration workflow — turns raw project ideas into implementation-ready feature briefs. See [plugins/architector/README.md](plugins/architector/README.md) for full documentation.

Pipeline: `/architector:new` -> `/architector:triage` -> `/architector:explore` <-> `/architector:map` -> `/architector:decide` -> `/architector:finalize` (with `/architector:status` and `/architector:audit` available anytime)

### workflow (v2.0 — tech-agnostic, dual-mode)

Tech-agnostic AI development workflow — interview, plan, implement, review, final-check, document, archive. Driven by `.ai-work/profile.json`. Operates manually or autonomously when an `orchestrator-context.json` sentinel is present. See [plugins/workflow/README.md](plugins/workflow/README.md).

Pipeline: `/workflow:interview` -> `/workflow:deep-plan` -> `/workflow:implement` -> `/workflow:review` -> `/workflow:final-check` -> `/workflow:document-work-result` -> `/workflow:compact-work`

KB integration (`update-kb-document`) was removed in v2.0 — replaced by `profile.json`, `project-context.md`, and `code-map.json`.

### orchestrator-team-lead

Autonomous team-lead that drives the workflow pipeline over a queue of feature briefs from architector. Each pipeline step runs as an isolated fresh-context Task agent. Includes interview-question routing through Haiku router and Opus expert agents, per-phase token budget check, escalation policy, and auto-maintained code-map. See [plugins/orchestrator-team-lead/README.md](plugins/orchestrator-team-lead/README.md).

Skills: `/orchestrator:bootstrap` (one-time setup) -> `/orchestrator:run` (loop driver). Internal helpers: `/orchestrator:router`, `/orchestrator:expert`, plus non-user-facing `code-map-update`, `code-map-indexer`, `profile-derive`.

Full design contract: [doc/architecture.md](doc/architecture.md).
