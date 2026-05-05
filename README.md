# getleverage

Community plugin marketplace for Claude Code.

## Installation

```bash
claude plugin marketplace add romadanylchuk/getleverage
```

## Available Plugins

| Plugin | Category | Description |
|--------|----------|-------------|
| [architector](plugins/architector/) | development | Multi-session architecture exploration — turn raw ideas into implementation-ready feature briefs |
| [workflow](plugins/workflow/) | development | Tech-agnostic AI development workflow — interview, plan, implement, review, final-check, document, archive. Manual or autonomous via orchestrator-team-lead. |
| [orchestrator-team-lead](plugins/orchestrator-team-lead/) | development | Autonomous team-lead that drives the workflow plugin's pipeline over a queue of feature briefs, with isolated fresh-context agents per step and a per-phase token-budget check |

## Installing a Plugin

```bash
claude plugin install architector@getleverage
claude plugin install workflow@getleverage
claude plugin install orchestrator-team-lead@getleverage
```

## Contributing a Plugin

See [CLAUDE.md](CLAUDE.md) for contributor guidelines.

### Quick start

1. Create `plugins/<your-plugin>/` with a `.claude-plugin/plugin.json` and a `skills/` directory
2. Add an entry to `.claude-plugin/marketplace.json`
3. Open a PR

## License

MIT
