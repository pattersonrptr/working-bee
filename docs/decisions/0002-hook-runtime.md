# 0002. Hooks in standard-library Python, launched by a probing bash script

Date: 2026-11-24. Status: accepted.

## Context

Hooks run on Linux, macOS and Windows, before many tool calls, and must work right after installation, with no
setup. The author's projects are Python-first, and the hooks this repository started from were Python.

On Windows, `python3` is often a Microsoft Store stub that exits 49 without running anything. Claude Code treats
that as a non-blocking error, so a guard launched with `python3` is silently off. On some Linux systems,
`python` is Python 2. Claude Code runs hook commands with bash (Git Bash on Windows).

## Decision

- Hooks are Python 3.9+ with the standard library only: no `pip install`, nothing to break on update.
- `hooks.json` calls `bash "${CLAUDE_PLUGIN_ROOT}/hooks/run.sh" <hook>.py`. The launcher probes `python3`, `python`
  and `py -3` for a real Python 3.9+, caches the winner in `$CLAUDE_PLUGIN_DATA/python-cmd`, and runs the hook with
  `-I` (isolated mode).
- Deny: exit 2 with the reason on stderr. Ask: exit 0 with `permissionDecision: "ask"` JSON on stdout.
- Unexpected errors fail open (exit 0). `WORKING_BEE_DEBUG=1` re-raises; tests always set it.
- If no Python is found, the launcher exits 1 and says so. The session brief puts the warning in the session
  context, so Claude tells the user that the guardrails are off.

## Consequences

- Python 3.9 or newer is a requirement, stated in each README.
- About 190 ms per guarded tool call on Windows with the cache (about 400 ms without it).
- Native PowerShell without Git Bash is not supported. Claude Code on Windows normally has Git Bash.
