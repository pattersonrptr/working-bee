---
name: audit-settings
description: Audits Claude Code configuration (user, project and local settings, hooks, plugins, MCP servers) for leaked secrets, over-broad permissions, broken or duplicated hooks and risky defaults, and reports findings with fixes. Use when the user asks to review, audit or harden their Claude settings, before sharing a repository, or after enabling working-bee core in a project that already had its own hooks.
argument-hint: "[project|user|all]"
allowed-tools: Read, Glob, Grep, Bash(git ls-files:*), Bash(git check-ignore:*)
---

# Audit Claude Code settings

Scope: `$ARGUMENTS` (default `all`). `project` = the files in this repository; `user` = `~/.claude/`.

## Files to read

| Level | Files |
|---|---|
| User | `~/.claude/settings.json`, `~/.claude/CLAUDE.md` |
| Project | `.claude/settings.json`, `.mcp.json`, `CLAUDE.md`, `AGENTS.md`, `.claude/working-bee.json`, `.claude/hooks/`, `.claude/agents/`, `.claude/skills/` |
| Local | `.claude/settings.local.json`, `CLAUDE.local.md` |

Skip files that do not exist. Do not read `.env` or key files: working-bee core blocks it, and you do not need their content.

## Rules

- **Never print a secret value.** Report where it is (file and JSON path, e.g. `env.GITHUB_TOKEN`) and its kind, never the value or part of it.
- **Read only.** Report and propose; change a file only if the user then asks, one finding at a time.
- Check every item in [references/checklist.md](references/checklist.md). Read it before you start.

## Report

One table, most severe first:

| Severity | Where | Finding | Fix |
|---|---|---|---|

Severity: **high** (a secret exposed or a guard that silently does nothing), **medium** (broader than needed, or will surprise someone), **low** (tidiness). End with the count per severity and the single change with the best value for the effort. If nothing is found, say so plainly.
