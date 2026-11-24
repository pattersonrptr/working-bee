# Claude Code, mapped

What each piece is, when to reach for it, and where it lives. Written while building working-bee; each section
links to the plugin that uses it. Facts checked against the official docs (code.claude.com/docs) and CLI 2.1.331
on 2026-11-24.

## Where configuration lives

| Level | Location | Applies to | Put here |
|---|---|---|---|
| Managed | system policy | everyone, cannot be overridden | company rules (not used here) |
| User | `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, `~/.claude/skills/` | all your projects | personal taste: model, language, status line |
| Project | `.claude/settings.json`, `CLAUDE.md` / `AGENTS.md`, `.claude/skills/`, `.claude/agents/`, `.mcp.json` (committed) | whoever opens the repo | facts and rules of **this** repo; which plugins to enable |
| Local | `.claude/settings.local.json`, `CLAUDE.local.md` (git-ignored) | you, in this repo | personal tweaks, experiments |

Precedence for settings: managed > command line > local > project > user. `CLAUDE.md` files are not overridden but
**concatenated**: all of them load, so contradictions between levels are yours to avoid.

A **plugin** is not a level. It is a package that is *enabled* at the user, project or local level
(`enabledPlugins`), and brings hooks, skills, agents, MCP servers and more with it. A **marketplace** is a git
repository (or folder) with a catalog of plugins.

Rule of thumb: you would copy it to the next project → plugin. Only makes sense in this repo → project. Personal
taste → user.

## Building blocks

| Piece | What it is | Use it when | Lives in |
|---|---|---|---|
| `CLAUDE.md` / `AGENTS.md` | Instructions loaded into every session | Facts and rules that always apply (commands, conventions, never-do) | repo root, `~/.claude/` |
| Skill | A folder with `SKILL.md`: instructions plus optional scripts and references, loaded **on demand** when its `description` matches, or by `/name` | A procedure you repeat (audit, release, triage) and don't want in every session's context | `skills/<name>/SKILL.md` |
| Subagent | A Claude with its own context window, prompt, tools and model, called by the main session | Work that would flood the main context (search, review) or needs a narrower role or cheaper model | `agents/<name>.md` |
| Hook | A command Claude Code runs on an event (before a tool, at session start, before compaction...) | Something must happen **every time**, deterministically: a model can forget an instruction, a hook can't | `hooks/hooks.json` (plugin) or `hooks` in settings |
| MCP server | A process that gives Claude new tools (APIs, databases, browsers) | Claude needs to reach a system it cannot via the shell | `.mcp.json` |
| Plugin | A package of the above with a manifest (`.claude-plugin/plugin.json`) and options | You want to reuse a set of these across projects or share them | a marketplace |
| Marketplace | A catalog (`.claude-plugin/marketplace.json`) listing plugins and where to get them | You have more than one plugin, or want others to install yours | a git repo |

**Instruction or hook?** If breaking the rule is merely bad, write it in `AGENTS.md`. If breaking it is expensive
or irreversible (a push to `main`, a leaked `.env`), make it a hook.

## Hooks in practice ([core](../plugins/core/))

- The event arrives as **JSON on stdin**: `tool_name`, `tool_input`, `cwd`, `hook_event_name`... Not environment
  variables.
- **Exit 2** blocks (PreToolUse) and stderr goes back to Claude as the reason. Exit 0 lets it through, and stdout
  may carry JSON. Any other code is a non-blocking error: the call proceeds.
- **Ask instead of block:** print `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision":
  "ask", "permissionDecisionReason": "..."}}`. Decisions combine as deny > defer > ask > allow.
- **SessionStart** stdout becomes context for the session. **PreCompact** stdout becomes instructions for the
  compaction summary.
- **PostToolUse** ([python-backend](../plugins/python-backend/)) runs after the tool, so it cannot stop it.
  `{"decision": "block", "reason": "..."}` puts the reason next to the tool result, for Claude to act on (lint
  errors left after a formatter); `hookSpecificOutput.additionalContext` adds a note; exit 2 shows stderr.
- `matcher` is a regex on the tool name (`Bash|PowerShell`, `Edit|Write`).
- Plugin hooks get `CLAUDE_PLUGIN_ROOT` (the installed plugin, changes on update), `CLAUDE_PLUGIN_DATA`
  (persistent storage), `CLAUDE_PROJECT_DIR` and `CLAUDE_PLUGIN_OPTION_<KEY>` in their environment.

## Skills in practice ([memory](../plugins/memory/))

- `SKILL.md` frontmatter: `name` (matches the folder), `description` (what it does **and when to use it**: this is
  all Claude sees until the skill loads, so it decides whether the skill triggers), `argument-hint`,
  `allowed-tools` (tools usable without a prompt while the skill runs).
- `$ARGUMENTS` in the body is replaced by whatever follows `/plugin:skill`. `${CLAUDE_SKILL_DIR}` (the skill's
  folder), `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PROJECT_DIR}` are replaced too: that is how
  [bootstrap](../plugins/bootstrap/) finds the templates it copies.
- A plugin skill also answers to its bare name (`/bootstrap`) when no other command uses it.
- Plugin skills are namespaced: `/memory:learn`. Claude can also invoke them on its own when the description
  matches the situation.
- **Progressive disclosure:** keep `SKILL.md` short and link to `references/*.md`, which Claude reads only when
  needed. Context is the budget.
- Slash skills work in headless mode too: `claude -p "/memory:agents-md audit"`.
- `CLAUDE.md` can import other files with `@path`: `CLAUDE.md` containing `@AGENTS.md` keeps one source of truth
  for every coding agent.

## Plugins and options

- `plugin.json`: only `name` is required; set `version` (semver) so users get explicit updates
  ([ADR 0001](decisions/0001-versioning.md)).
- `userConfig` declares options (`string`, `number`, `boolean`, `directory`, `file`; `sensitive` ones go to the OS
  keychain). Values are saved in the **user's** settings, so they are personal, not per project. Per-project rules
  need a project file ([ADR 0003](decisions/0003-project-settings-file.md)).
- `dependencies` lists plugins installed along with this one: `["core"]` resolves in the same marketplace, and
  `claude plugin install memory@working-bee` reports "+ 1 dependency: core".
- `claude plugin validate <path> --strict` checks manifests, skills, agents and hooks; `claude plugin details`
  shows the token cost of a plugin; `claude plugin eval` runs eval suites with and without the plugin.
- A project declares a marketplace with `"extraKnownMarketplaces": {"working-bee": {"source": {"source": "github",
  "repo": "owner/repo"}}}` and switches plugins on with `enabledPlugins`; both apply only after the folder is trusted.
- A local-path marketplace reads the folder directly: edits apply on the next session or `/reload-plugins`.
- `claude --plugin-dir plugins/<name> -p "..."` loads one plugin for a single run: the quickest end-to-end test of
  a hook against a real Claude Code.

## Orchestration (planned: phases 4 and 5)

- **Subagents** run inside one session and report back. Good for parallel review or search.
- **Worktrees** (`claude -w`, or the `isolation: worktree` option for agents) give parallel workers separate
  checkouts, so they don't trample each other's files.
- **Background sessions** (`claude --bg`, `claude agents`) keep working while you do something else.
- **Agent teams**: several Claude sessions that coordinate through a shared task list and message each other.
  Experimental and off by default; enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
- **Workflows**: plugins can ship `workflows/*.js`, scripted multi-step orchestrations. To be studied in phase 5.

## Glossary

- **Fail-open**: on an unexpected error, let the action through. Right for helpers; wrong for a lock.
- **Dogfooding**: this repository uses its own plugins.
- **Hat**: a plugin for a stack or role (python-backend, privacy) that a project switches on. Solo developers wear
  many hats; teams split them among people.
