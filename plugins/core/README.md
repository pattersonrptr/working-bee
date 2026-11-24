# core

Guardrails and session context for Claude Code. Every other working-bee plugin depends on it.

## What it does

| Hook | Event | Effect |
|---|---|---|
| `guard_commands` | PreToolUse (Bash, PowerShell) | **Denies** commits and pushes to protected branches, force pushes to them, `push --mirror`, `--no-verify`, `gh pr merge --admin`, recursive deletes of `/`, `~`, `.` or a drive, printing secret files (`cat .env`) and staging them. **Asks** before force pushes to other branches, `push --all`, `reset --hard` and `clean -f`. |
| `guard_files` | PreToolUse (Read, Grep, Edit, Write, MultiEdit, NotebookEdit) | **Denies** reading or writing secret files (`.env`, `.env.*` except templates, `*.pem`, `*.key`, SSH private keys, `.netrc`), anywhere. **Denies** edits to `frozen_paths` that already exist on a protected branch. **Asks** before edits to the guardrails' own configuration. |
| `session_brief` | SessionStart | Adds the branch, changed files, open PRs and the files to read first to the session context. |
| `pre_compact` | PreCompact | Asks the compaction summary to keep the branch, uncommitted files and recent commits. |

Skill: **`/core:audit-settings [project|user|all]`** reviews your Claude Code settings for leaked secrets, over-broad permissions and broken or duplicated hooks.

Denied calls exit with code 2 and Claude sees the reason. If a hook crashes it lets the call through (fail-open), so a bug never stops your work; `WORKING_BEE_DEBUG=1` makes crashes loud.

## Requirements

- Python 3.9+ (standard library only). The launcher tries `python3`, `python` and `py -3`, and skips the Windows Store stub.
- `bash` (on Windows, Git Bash, which Claude Code uses for hooks).
- Optional: `gh` for open PRs in the brief.

## Settings

Three layers, the last one wins:

1. Defaults: protected branches `main` and `master`.
2. Plugin options, per user (`/plugin` → core → configure, or `claude plugin configure core@working-bee`):
   - `protected_branches`: comma-separated, default `main,master`;
   - `brief_open_prs`: default `true`.
3. The project's `.claude/working-bee.json`, committed with the repository:

```json
{
  "core": {
    "protected_branches": ["main"],
    "frozen_paths": ["backend/alembic/versions/*.py"],
    "ask_paths": ["infra/**"],
    "brief": { "open_prs": true, "read_first": ["docs/plan/README.md"] }
  }
}
```

`ask_paths` adds to the defaults (`.claude/settings*.json`, `.claude/hooks/**`, `.claude/working-bee.json`, `.githooks/**`, `.git/hooks/**`); the other keys replace them. Patterns use `*` within a folder and `**` across folders.

## Limits

These hooks are a seatbelt, not a sandbox. The command parsing is a heuristic: a determined `python -c "..."` can get around it. The real locks are branch protection on your git host and secrets that never sit in the repository.
