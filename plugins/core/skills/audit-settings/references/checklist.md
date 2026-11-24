# Audit checklist

Each item: what to look for, why it matters, the usual fix.

## Secrets

1. **Values that look like credentials** in any settings file: `env` entries whose name contains `TOKEN`, `KEY`, `SECRET`, `PASSWORD` or `PAT`, or values starting with `ghp_`, `github_pat_`, `sk-`, `xox`, `AKIA`, or containing `-----BEGIN`. High.
   Fix: move it to the OS keychain, a shell profile outside any repository, or a plugin option marked `sensitive`. Rotate it if the file was ever committed or shared.
2. **Secrets in committed files.** For project-level files, `git ls-files` shows whether they are tracked. A secret in a tracked file is high even if it was later deleted (history keeps it).
3. **Local files tracked by git.** `.claude/settings.local.json` and `CLAUDE.local.md` must not be in `git ls-files`, and `git check-ignore` should confirm they are ignored. Medium.
4. **MCP server config** (`.mcp.json`) with literal tokens in `env` or `headers`, instead of `${VAR}` expansion. High.

## Permissions

5. **Allow rules broader than needed:** `Bash(*)`, `Bash` with no pattern, `Bash(git:*)`, `Bash(curl:*)`, `Bash(python:*)`, `WebFetch` with no domain. They let any command of that family run without a prompt. Medium.
6. **Allow rules that defeat a guard:** for example `Bash(git push:*)` in allow is fine only while a hook (working-bee core) or branch protection on the host still stops pushes to protected branches. Note it, don't flag it as wrong.
7. **`defaultMode: bypassPermissions`** in a committed file. High: everyone who opens the repository runs without prompts.
8. **`enableAllProjectMcpServers: true`** in a committed file: any MCP server added to `.mcp.json` later starts without review. Medium.
9. **`Write(path)` in deny (or allow):** file permission checks only match `Edit(path)`, which covers every editing tool, so a `Write(...)` rule does nothing. Medium. Fix: use `Edit(path)`; add `Read(path)` to keep the file out of the context too.
10. **Missing deny for secrets:** no `Read(./.env)` / `Read(./.env.*)` deny and working-bee core not enabled. Medium.

## Hooks

11. **Hook scripts that do not exist** at the path a command points to. High: the hook errors (non-blocking) and the guard is silently off.
12. **Hooks reading an interface that does not exist**, such as environment variables like `CLAUDE_TOOL_NAME` or `CLAUDE_TOOL_INPUT`. Claude Code sends the event as JSON on stdin. High: the hook looks fine and never fires. Test: does the script read stdin?
13. **`python3` in a hook command on Windows:** it is often the Microsoft Store stub, which exits 49 without running the script. High on Windows. Fix: a launcher that probes for a real Python (working-bee core uses one).
14. **Hooks that block everything on unexpected input** (for example "exit 2 when not in a git repository"). Medium: they stop work for unrelated reasons.
15. **Duplicated guards:** a project hook that does what working-bee core already does (git guard, `.env` guard, session brief), once core is enabled. Low: double messages, double cost. Fix: remove the project hook and move project-specific rules to `.claude/working-bee.json` (`protected_branches`, `frozen_paths`, `ask_paths`, `brief.read_first`).

## Plugins and memory

16. **Plugins from marketplaces nobody recognises** in `enabledPlugins` or `extraKnownMarketplaces`. Ask the user; a plugin runs code as them. Medium.
17. **`CLAUDE.md` / `AGENTS.md` over ~200 lines,** or rules that contradict each other between levels. Low: costs context every session and dilutes the rules that matter.
18. **Personal preferences in project files** (language, model, voice) or project facts in user files. Low: the level table is in the working-bee docs (`docs/concepts.md`).
