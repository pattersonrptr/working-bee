# bootstrap

One command to get a repository ready for Claude Code with working-bee, so no project starts from a blank
`.claude/` again.

## Install

```
/plugin install bootstrap@working-bee
```

It depends on `core` and `memory`, which are installed with it. Install it at user scope: it is the plugin you
use *before* a project has any settings.

## Use

```
/bootstrap                       # looks at the stack and asks
/bootstrap python-backend privacy
```

1. **Looks** at the repository: stack (Python, Node, Go, Rust, Terraform), default branch, what already exists.
2. **Asks once**: which hats (plugins) to switch on, which branches to protect, which extras to add.
3. **Shows the plan** (create / merge / skip for each file) and waits for your OK.
4. **Writes**, never overwriting:

| File | What goes in |
|---|---|
| `.claude/settings.json` | the working-bee marketplace (`extraKnownMarketplaces`), `enabledPlugins`, and `permissions.allow` only for test and lint commands the repo really uses. Merged into an existing file. |
| `.claude/working-bee.json` | per-project rules (protected branches, frozen paths, docs to read first), only when they differ from the defaults |
| `AGENTS.md`, `CLAUDE.md` | through `/memory:agents-md init` (or an audit, if they exist) |
| `docs/gotchas.md` | the header, ready for `/memory:gotcha` |
| `.github/pull_request_template.md` | what and why, how it was checked, risks |
| `tools/privacy_check.py`, `.githooks/pre-commit` | optional, with `privacy`: the same check this marketplace runs on itself |
| `.gitignore` | `.env`, `.claude/settings.local.json`, `CLAUDE.local.md` if missing |

5. **Reports** what changed and the one-time commands each machine runs to install the plugins.

Nothing is committed or pushed.
