# Gotchas

Surprises that cost time. Each one: what happens, why, what to do. The date says when it was last verified.

## Hooks

- **`python3` on Windows can be the Microsoft Store stub** (verified 2026-11-24). It prints "Python was not found"
  and exits 49. Claude Code treats any exit other than 0 or 2 as a non-blocking error, so the call goes through
  and **the guard is silently off**. Fix: `plugins/core/hooks/run.sh` probes `python3`, `python` and `py -3` for
  a real Python 3.10+ and caches the winner in `$CLAUDE_PLUGIN_DATA`.
- **A fail-open hook that crashes looks exactly like one that allowed the call** (2026-11-24). Tests of "this must
  pass" would pass vacuously. Fix: `WORKING_BEE_DEBUG=1` makes hooks re-raise; the test suite always sets it.
- **Hooks read the event from stdin, not from environment variables** (2026-11-24). Scripts that read invented
  variables (such as `CLAUDE_TOOL_NAME`) never fire and look fine. `/core:audit-settings` checks for this.
- **`python -I` removes the script's own folder from `sys.path`** (2026-11-24). Isolated mode is worth it (no
  `PYTHONPATH` surprises), so each hook inserts its own folder before importing `_common`.
- **Probing for Python on every call costs ~250 ms on Windows** (2026-11-24). PreToolUse hooks run before every
  matching tool call; the launcher cache brings a call down to ~190 ms.
- **`${CLAUDE_PLUGIN_ROOT}` arrives with backslashes on Windows** (2026-11-24): `C:\...\plugins\core/hooks/run.sh`.
  Git Bash accepts it as long as it is quoted.
- **`${user_config.KEY}` is an error inside a shell-form hook command** (docs, 2026-11-24). Read the environment
  variable `CLAUDE_PLUGIN_OPTION_KEY` instead.
- **Hook environment variables do not exist in the Bash tool** (docs, 2026-11-24). `CLAUDE_PLUGIN_ROOT` and friends
  are set for hook processes only.
- **The Grep tool with no `path` searches the whole project** (2026-11-24). `guard_files` only sees the path
  argument. ripgrep skips git-ignored files by default, so keep `.env` in `.gitignore`.

- **A formatter in PostToolUse does not break Claude's next Edit** (verified 2026-11-24). Claude Code notices the
  file changed after the edit and tells Claude so ("likely a formatter... Read the file first" if the next
  `old_string` targets a reformatted region). No workaround needed.

## Plugins and marketplaces

- **An installed plugin cannot reach another plugin's files** (2026-11-24). `${CLAUDE_PLUGIN_ROOT}` is per plugin,
  in its own cache folder, so a dependency's `run.sh` is out of reach. Each plugin with hooks ships a copy of
  core's launcher; `tests/test_manifests.py` fails if a copy drifts.

- **`hooks/hooks.json` must wrap the events in a top-level `"hooks"` key** (docs, 2026-11-24); an inline `hooks`
  object in `plugin.json` must not. `tests/test_manifests.py` checks the file.
- **Plugin options (`userConfig`) are stored in the user's settings** (docs, 2026-11-24), so they cannot vary by
  project. Per-project rules live in `.claude/working-bee.json` ([ADR 0003](decisions/0003-project-settings-file.md)).
- **`claude plugin install` reports options "not yet set" even when they have defaults** (2026-11-24). The hooks
  keep their own defaults, so an unset option never changes behavior.
- **`claude plugin validate --strict` fails without a `version`** (2026-11-24). See
  [ADR 0001](decisions/0001-versioning.md).
- **`enabledPlugins` in a project's settings is not an installation** (2026-11-24). Each machine still runs
  `claude plugin install core@working-bee --scope project` once (which also rewrites the key order of
  `.claude/settings.json`: restore it with git if you care about the diff). A plugin that works may just be riding
  on an install made somewhere else.
- **A local-path marketplace ignores the version pin** (docs, 2026-11-24): edits apply on the next session or
  `/reload-plugins`, which is what you want while developing.

## Permissions

- **`Write(path)` deny rules are ignored** (Claude Code warning, 2026-11-24): file permission checks only match
  `Edit(path)`, which covers every file-editing tool. `Read(path)` is separate. `/core:audit-settings` flags it.
- **`claude -p` in a folder never opened interactively ignores the project's `permissions.allow`** (verified
  2026-11-24). It prints "Ignoring 3 permissions.allow entries from .claude/settings.json: this workspace has not
  been trusted." Allow rules only apply after the trust dialog is accepted once interactively (or
  `hasTrustDialogAccepted` is set in `~/.claude.json`). Plugins and hooks still load, so only the permissions
  differ. Fix: open the folder once with `claude` and accept the dialog before testing non-interactively.

## Skills

- **A skill that interviews the user cannot do so in `claude -p`** (2026-11-24). For headless tests, put the answers
  in the prompt and say the user pre-approves the writes. That is what `/memory:agents-md init` was tested with.
- **A checklist that names a mechanism will be applied too widely** (2026-11-24). The audit suggested `ask_paths`
  (file paths) to guard a deploy command. Say exactly what each guard covers in the reference files.

## CI

- **GitHub's `ubuntu-latest` (Ubuntu 26.04) has no Python 3.9** (2026-11-24): `setup-python` fails in seconds with
  "version '3.9' ... was not found". 3.9 is past end of life; the minimum is now 3.10.
- **On a private repository, macOS runners use minutes 10x and Windows 2x.** The full matrix costs about 15 billed
  minutes per run; drop macOS from pull requests if the free quota gets tight.

## Windows and git

- **A CRLF in a shell script breaks bash** (`$'\r': command not found`). This machine has `core.autocrlf=true`;
  `.gitattributes` forces LF for every text file.
- **`subprocess.run(["bash", ...])` on Windows can start WSL's bash** (2026-11-24): Windows looks in System32
  before `PATH`. WSL cannot see `C:/` paths, so the call fails with "No such file or directory". Use the full path
  from `shutil.which("bash")`.
