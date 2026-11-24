# working-bee

> A **working bee** is what Australians call a mutirão: neighbours turning up to get done together what nobody
> would finish alone. Here the neighbours are agents, and the barn is your project.

Claude Code plugins for a developer who works solo but wants the habits of a team: guardrails that stop the
expensive mistakes, project memory that turns errors into rules, a one-command project bootstrap, reviewer
subagents and parallel orchestration. Configure once, reuse in every repository.

**Status:** early. `core` and `memory` work; the rest is on the [roadmap](docs/roadmap.md).

## Plugins

| Plugin | What it gives you | Status |
|---|---|---|
| [`core`](plugins/core/) | Guardrails for git, shell and secret files; a session brief; git facts kept across compaction; `/core:audit-settings` | ✅ 0.1.0 |
| [`memory`](plugins/memory/) | `/memory:learn` (a mistake becomes a one-line rule), `/memory:gotcha`, `/memory:agents-md init\|audit\|update` | ✅ 0.1.0 |
| `bootstrap` | `/bootstrap`: a new repository configured in minutes | planned |
| `dev-workflow` | planner, implementer, QA and adversarial reviewer subagents; `/plan`, `/slice`, `/review`, `/deliver` | planned |
| `python-backend`, `privacy` | stack and privacy "hats" a project switches on | planned |

## Install

From a local clone:

```
claude plugin marketplace add ./working-bee
claude plugin install core@working-bee
```

Inside Claude Code: `/plugin marketplace add ./working-bee`, then `/plugin install core@working-bee`.
Use `--scope project` to enable it for everyone who opens a repository, or `--scope local` just for you.

Per-project rules (protected branches, frozen files, files to read first) go in `.claude/working-bee.json`;
see the [core README](plugins/core/README.md).

## Development

```
python -m pytest -q                      # hook tests (subprocess, real event JSON)
claude plugin validate . --strict        # catalog and manifests
git config core.hooksPath .githooks      # privacy check before every commit
```

How Claude Code's pieces fit together: [docs/concepts.md](docs/concepts.md). Surprises that cost time:
[docs/gotchas.md](docs/gotchas.md). Decisions: [docs/decisions/](docs/decisions/).

## License

[MIT](LICENSE).
