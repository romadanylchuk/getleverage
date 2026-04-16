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

### workflow

AI development workflow — structured pipeline from feature interview to implementation, review, and archival. See [plugins/workflow/README.md](plugins/workflow/README.md) for full documentation.

Pipeline: `/workflow:interview` -> `/workflow:deep-plan` -> `/workflow:implement` -> `/workflow:review` -> `/workflow:final-check` -> `/workflow:document-work-result` -> `/workflow:update-kb-document` -> `/workflow:compact-work`
