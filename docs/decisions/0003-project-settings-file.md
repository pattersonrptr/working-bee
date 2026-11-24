# 0003. Per-project rules in `.claude/working-bee.json`

Date: 2026-11-24. Status: accepted.

## Context

Some guardrail rules are personal ("I protect `main` and `master` everywhere"). Others belong to one repository:
"Alembic migrations already on `main` are frozen", "read `docs/plan/README.md` before planning".

Plugin options (`userConfig`) are saved in the **user's** settings, so they apply to every project alike. Putting
project rules in hook scripts inside each repository is exactly the per-project setup this marketplace exists to
remove.

## Decision

Hooks read three layers, the last one wins:

1. Defaults in `plugins/core/hooks/_common.py`.
2. Plugin options (`CLAUDE_PLUGIN_OPTION_*`): personal defaults.
3. `.claude/working-bee.json`, committed with the project, one object per plugin (`{"core": {...}}`).

Lists replace the earlier layer, except `ask_paths`, which adds to the defaults so that a project cannot drop the
protection of the guardrails' own files. An invalid file falls back to the other layers, and the session brief
warns about it.

## Consequences

- A repository's guardrail rules are reviewed in pull requests like any other code.
- Editing `.claude/working-bee.json` always asks the user (it is one of the default `ask_paths`).
- Every future plugin reads its own key from the same file. There is one file to learn, not one per plugin.
