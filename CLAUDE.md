# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Architector is a **multi-session architecture exploration workflow** implemented as a set of Claude Code skills. It turns raw project ideas into implementation-ready feature briefs. There is no build system, no tests, no runtime code — only skill definitions (SKILL.md files) that Claude Code loads as slash commands.

## Skill Pipeline

The skills form a linear pipeline with a feedback loop in the middle:

```
/arch-init → /arch-explore ⇄ /arch-map → /arch-decide → /arch-finalize
                              /arch-status (read-only, anytime)
```

Each skill reads/writes to a `.ai-arch/` directory in the user's project (not this repo).

## Skill Inventory

| Skill | Dir | Recommended Model | Modifies `.ai-arch/`? |
|-------|-----|-------------------|----------------------|
| `/arch-init` | `arch-init/` | Opus | Yes — creates initial structure |
| `/arch-explore` | `arch-explore/` | Opus | Yes — updates node notes and maturity |
| `/arch-decide` | `arch-decide/` | Opus | Yes — adds decisions, advances maturity |
| `/arch-map` | `arch-map/` | Sonnet | Yes — updates connections |
| `/arch-status` | `arch-status/` | Sonnet | No — read-only |
| `/arch-finalize` | `arch-finalize/` | Opus | Yes — creates feature briefs and todo list |

## Key Concepts

- **Idea nodes** (`raw-idea → explored → decided → ready`): The unit of work. Each is a `.md` file in `.ai-arch/ideas/`.
- **Priority levels** (`blocking > core > extension > deferred`): `blocking` nodes gate `/arch-finalize`.
- **Connections** (dependency, shared concern, conflict, merge/split candidates): Tracked in both node files and `index.json`.
- **Feature briefs**: Output of `/arch-finalize`, each maps to one run of the implementation workflow (`/interview → /deep-plan → /implement`).

## Architecture Constraints

- Skills must never act outside their role: `/arch-explore` cannot make decisions, `/arch-decide` cannot explore, `/arch-map` never decides.
- `/arch-decide` must always wait for explicit user confirmation before locking in a choice.
- `/arch-finalize` has a hard gate: all `blocking` nodes must be `ready`.
- `/arch-explore` always shows the dashboard before any exploration.
- `/arch-status` is strictly read-only.

## Editing Skills

Each skill is entirely self-contained in a single `SKILL.md` file with YAML frontmatter (`name`, `description`) followed by the skill definition. When modifying a skill, respect the separation of concerns between skills — do not add decision-making to exploration, exploration to mapping, etc.
