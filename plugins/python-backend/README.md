# python-backend

The Python hat. Every Python file Claude edits comes out fixed and formatted by the project's own ruff, and the
problems ruff cannot fix go straight back to Claude, next to the edit that caused them.

## Install

```
/plugin install python-backend@working-bee
```

It depends on `core`, which is installed with it.

## What it does

| Part | What it does |
|---|---|
| Hook (after `Edit`/`Write`) | Runs `ruff check --fix` and then `ruff format` on the `.py`/`.pyi` file just changed, from the project root, so `pyproject.toml` or `ruff.toml` applies. Excluded paths stay excluded. Problems ruff could not fix are shown to Claude (up to 20 lines). Files outside the project are left alone. |
| `/python-backend:test [target]` | Runs pytest with the project's runner (`uv run`, `poetry run`, `.venv` or `python -m`), the tests related to the change first and then the whole suite. Never weakens a test to make it pass. |

If ruff is not installed, Claude is told once per session and nothing else happens. The hook never installs
anything and makes no network calls (no `uvx`).

## Which ruff runs

| `runner` | Command |
|---|---|
| `auto` (default) | the project's `.venv`, then `poetry run ruff` if there is a `poetry.lock`, then `ruff` on PATH |
| `venv` | the project's `.venv`, then `ruff` on PATH |
| `uv` | `uv run --no-sync ruff` (never syncs) |
| `poetry` | `poetry run ruff` |
| `path` | `ruff` on PATH |

## Settings

Personal default: the plugin option `runner`. Per project, in `.claude/working-bee.json`:

```json
{
  "python-backend": {
    "runner": "uv",
    "fix": true,
    "format": true,
    "report": true
  }
}
```

`fix: false` stops `--fix`, `format: false` stops `ruff format`, and `report: false` keeps the remaining problems
to yourself.
