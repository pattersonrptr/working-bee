# AGENTS.md structure

Aim for a file a new teammate could read in three minutes and then work safely. Agents read all of it, every
session: each line costs context and competes for attention.

## Sections (in this order; drop the ones that do not apply)

```markdown
# <Project> — working agreement for coding agents

<Two or three sentences: what the project is, who it is for, its current stage.>
<Who decides what: "The author decides product and architecture; the agent proposes, implements and verifies.">

## Repository map

| Folder | What it is |
|---|---|

## Commands

| Task | Command (from which folder) |
|---|---|
| Install / run / test / lint / build | ... |

## Always
- <habits for every task: verification before done, commit message format, language of docs>

## Ask first
- <actions that need consent: pushes, new dependencies, schema or data changes, deleting files>

## Never
- <prohibitions, with the reason when not obvious>

## Known traps
- <one line each; details in docs/gotchas.md>
```

## Principles

- **Facts over adjectives.** "Python 3.12, FastAPI, Postgres 16 on port 5434" beats "a modern backend".
- **Commands are copy-pasteable** and verified against the config files.
- **Point, don't paste.** Long explanations live in `docs/`. AGENTS.md has a one-line pointer ("Before touching
  auth, read docs/auth.md").
- **No secrets, no personal data**, not even as examples: the file is committed and read by every tool.
- **Nested files** (`web/AGENTS.md`) are for folders with their own stack and commands. Keep the root one short.
- **Claude-only settings** (hooks, permissions, skills, plugins) go in `CLAUDE.md` or `.claude/`, not in AGENTS.md.

## CLAUDE.md that imports it

```markdown
@AGENTS.md

## Claude Code only

- <hooks and plugins in use and what they enforce, skills worth knowing, permission notes>
```
