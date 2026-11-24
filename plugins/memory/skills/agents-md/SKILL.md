---
name: agents-md
description: Creates, audits or updates a project's AGENTS.md (the instructions every coding agent reads) and the CLAUDE.md that imports it. Use when a repository has no AGENTS.md or CLAUDE.md, when they feel long, stale or contradictory, after a change that makes them out of date (new commands, folders or conventions), or when the user runs /agents-md.
argument-hint: "init | audit | update"
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(git log:*), Bash(git diff:*), Bash(git ls-files:*), Bash(git status:*)
---

# AGENTS.md: init, audit, update

Mode: `$ARGUMENTS` (`init`, `audit` or `update`). If empty: `init` when there is no AGENTS.md, otherwise `audit`.

**Why AGENTS.md:** it is the cross-tool convention (Codex, Copilot, Cursor and others read it). Claude Code reads
`CLAUDE.md`, so `CLAUDE.md` holds `@AGENTS.md` plus anything that only applies to Claude Code.

Read [references/structure.md](references/structure.md) before `init` or `update`, and
[references/audit-checklist.md](references/audit-checklist.md) before `audit`.

## init

1. **Learn the repository from evidence**, not guesses: README, `git ls-files` (top-level layout), build and test
   config (`package.json`, `pyproject.toml`, `Makefile`, `docker-compose*.yml`, CI workflows), existing docs, the
   last ~30 commit subjects (conventions). Do not open data, backups, dumps, `.env` or anything that may hold
   personal data: the file list is enough to know they exist.
2. **Ask the user** the few things the code cannot tell, in one round: what the project is for, who decides what,
   rules they care about (what must never happen, what needs their OK), and how they like to work (tests first? PR
   per change?).
3. **Draft** AGENTS.md with the structure in the reference, at most ~120 lines. Every command must come from
   config or docs you read. Mark anything unverified with `(unverified)`.
4. **CLAUDE.md:** if missing, create it with `@AGENTS.md`. If it exists with content, show what would move to
   AGENTS.md (cross-tool facts) and what stays (Claude Code specifics), and move only after the user agrees.
5. Show the draft, apply the user's corrections, then write the files. Do not commit.

## audit

Read AGENTS.md, CLAUDE.md, any `CLAUDE.local.md`, nested `AGENTS.md`/`CLAUDE.md` files and the imports they
reference. Check every item in the checklist and verify the commands against the real config. Report one table,
most severe first: `Severity | Where | Finding | Fix`. Change nothing unless the user asks.

## update

1. Find what changed since the file was last touched: `git log -1 --format=%H -- AGENTS.md`, then
   `git diff --stat <that>..HEAD` and the commit subjects since then.
2. Look for changes that make the file stale: new or renamed folders, scripts, commands, dependencies, CI jobs,
   conventions visible in recent commits.
3. Propose the edits as a list (add / change / remove, with the line), apply them after the user agrees, and keep
   the length budget: remove before you add.
