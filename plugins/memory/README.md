# memory

Project memory that improves with use. Mistakes turn into rules, surprises turn into documented gotchas, and the
instruction file every agent reads stays accurate and short.

## Install

```
/plugin install memory@working-bee
```

## Skills

| Skill | What it does |
|---|---|
| `/memory:learn [what went wrong]` | Turns a mistake (by default the last correction in the conversation) into a one-line, checkable rule in `AGENTS.md`, under the right section, after you confirm. Proposes a guard as well when the mistake is expensive. |
| `/memory:gotcha [the surprise]` | Adds an entry to `docs/gotchas.md`: bold symptom, date verified, cause and fix. Updates an existing entry instead of duplicating it. |
| `/memory:agents-md init\|audit\|update` | `init` drafts `AGENTS.md` from the repository's real config and a short interview, plus a `CLAUDE.md` that imports it. `audit` reports broken commands, contradictions, vague rules and bloat. `update` proposes edits from what changed in git since the file was last touched. |

Claude also invokes them on its own when the situation matches: after you correct it, after a quirk is solved, or
in a repository with no `AGENTS.md`. Nothing is written without your confirmation.

## Why AGENTS.md

It is the cross-tool convention: Codex, Copilot, Cursor and others read it. Claude Code reads `CLAUDE.md`, so
`CLAUDE.md` contains `@AGENTS.md` plus anything specific to Claude Code.

## Settings

Optional, in the project's `.claude/working-bee.json`:

```json
{
  "memory": {
    "target": "AGENTS.md",
    "gotchas": "docs/gotchas.md"
  }
}
```

Depends on [`core`](../core/), which is installed with it.
