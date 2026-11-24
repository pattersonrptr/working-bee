# Settings files written by /bootstrap

## `.claude/settings.json` (committed; applies to whoever opens the repository)

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "extraKnownMarketplaces": {
    "working-bee": {
      "source": { "source": "github", "repo": "pattersonrptr/working-bee" }
    }
  },
  "enabledPlugins": {
    "core@working-bee": true,
    "memory@working-bee": true,
    "python-backend@working-bee": true
  },
  "permissions": {
    "allow": [
      "Bash(uv run pytest:*)",
      "Bash(uv run ruff check:*)"
    ]
  }
}
```

- `enabledPlugins`: `core`, `memory` and each chosen hat, as `<plugin>@working-bee: true`.
- `permissions.allow`: only the read-only or test commands from [stacks.md](stacks.md) that match what the
  repository really uses (its lock file, Makefile or docs). Never `Bash(*)`, deploys, `git push`, or anything that
  writes outside the repository. When unsure, leave it out: a prompt is cheap.
- Do not add `deny` rules for secrets: `core` already blocks `.env` and keys for every tool.

### Merging into an existing file

- Keep every existing key and value, and its order. Add the missing keys at the end of each object.
- `enabledPlugins`: add the missing entries; never flip an existing `false` to `true` without asking.
- `permissions.allow`: append the missing rules; leave `deny` and `ask` untouched.
- An existing `working-bee` marketplace with another source: leave it and say so (it may be a local clone).
- Hooks already in the file that overlap core's guards (branch protection, `.env` blocks): list them in the
  report and suggest `/core:audit-settings`; do not remove them.

## `.claude/working-bee.json` (committed; per-project rules for the working-bee plugins)

Write only values that differ from the defaults. With the defaults (`main` and `master` protected, no hats with
settings) the file is not needed.

```json
{
  "core": {
    "protected_branches": ["main", "develop"],
    "brief": { "read_first": ["docs/architecture.md"] }
  },
  "python-backend": { "runner": "uv" }
}
```

| Key | When to write it |
|---|---|
| `core.protected_branches` | the protected branches chosen differ from `["main", "master"]` |
| `core.frozen_paths` | the user names files that must not change once on the default branch (applied migrations) |
| `core.brief.read_first` | docs every session should read before planning (a roadmap, an architecture doc) |
| `python-backend.runner` | the project's runner is known and `auto` would guess wrong (for example uv without a `.venv`) |

If the file exists, merge per key the same way as above.
