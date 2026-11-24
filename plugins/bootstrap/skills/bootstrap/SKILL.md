---
name: bootstrap
description: Prepares a repository for Claude Code with working-bee in one pass. It looks at the stack, asks which hats (plugins) to switch on, then writes or merges .claude/settings.json (marketplace, plugins, safe permissions), .claude/working-bee.json, AGENTS.md and CLAUDE.md (through /memory:agents-md), docs/gotchas.md, a PR template, .gitignore entries and an optional privacy pre-commit. Use when starting a new repository, when a repository has no .claude/settings.json or AGENTS.md, when the user wants guardrails or working-bee plugins set up in a project, or when the user runs /bootstrap.
argument-hint: "[hats to switch on, e.g. python-backend privacy]"
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(git rev-parse:*), Bash(git ls-files:*), Bash(git config --get:*), Bash(git symbolic-ref:*), Bash(git remote:*)
---

# Bootstrap a repository

Hats requested: `$ARGUMENTS` (may be empty). The project root is `${CLAUDE_PROJECT_DIR}`; files to copy are in
`${CLAUDE_SKILL_DIR}/assets/`.

**Never overwrite.** A file that exists is merged (settings, `.gitignore`) or left alone and reported. Nothing is
committed or pushed. Writes to `.claude/settings.json`, `.claude/working-bee.json` and `.githooks/` ask the user:
that is a guard working, not an error. If such a write is refused (headless runs cannot ask), print the exact
content to apply instead, and mark the file as pending in the report.

## 1. Look

- Is it a git repository? Default branch (`git symbolic-ref refs/remotes/origin/HEAD`, else the current one).
- Stack signals and the hat each suggests: [references/stacks.md](references/stacks.md).
- Which of these already exist: `.claude/settings.json`, `.claude/working-bee.json`, `AGENTS.md`, `CLAUDE.md`,
  `docs/gotchas.md`, `.github/pull_request_template.md`, `.gitignore`, `core.hooksPath` or another pre-commit
  setup (`.pre-commit-config.yaml`, `.husky/`, `lefthook.yml`).
- Do not open data, dumps, `.env` or anything that may hold personal data.

## 2. Ask once

One round of questions (skip what `$ARGUMENTS` already answers):

1. **Hats** (multi-select): the ones the stack suggests, pre-selected, plus `privacy`, recommended when the
   project touches an employer's, a client's or anyone's personal data. `core` and `memory` always come.
2. **Protected branches**: the default branch found in step 1 (plus `main`/`master` if they exist).
3. **Extras** (multi-select): PR template, `docs/gotchas.md`, privacy pre-commit (only offered if `privacy` is
   chosen and no other pre-commit setup exists).

## 3. Show the plan, then write

List each file with **create**, **merge** or **skip (exists)**, and wait for one confirmation. Then:

1. `.claude/settings.json` and `.claude/working-bee.json`: shapes and merge rules in
   [references/settings.md](references/settings.md).
2. `AGENTS.md` / `CLAUDE.md`: if `AGENTS.md` is missing, follow `/memory:agents-md init`. If it exists, offer
   `/memory:agents-md audit` instead of touching it.
3. `docs/gotchas.md`: the header from `/memory:gotcha`, nothing else.
4. `.github/pull_request_template.md`: copy `assets/pull_request_template.md`.
5. Privacy pre-commit: copy `assets/tools/privacy_check.py` to `tools/privacy_check.py` and
   `assets/githooks/pre-commit` to `.githooks/pre-commit`, then tell the user to run
   `git config core.hooksPath .githooks` once per clone (and `chmod +x .githooks/pre-commit` outside Windows).
   The check reads the same `.git/info/sensitive-terms` as the `privacy` hook; offer to create that file empty
   and never fill it with guesses.
6. `.gitignore`: add whichever is missing of `.env`, `.env.*`, `!.env.example`, `.claude/settings.local.json`,
   `CLAUDE.local.md`.

## 4. Report

A table of what was created, merged and skipped. Then the one-time setup for each machine, with the chosen hats:

```
claude plugin marketplace add pattersonrptr/working-bee
claude plugin install core@working-bee --scope project
claude plugin install memory@working-bee --scope project
claude plugin install <hat>@working-bee --scope project   # one line per hat
```

Open the folder once with `claude` and accept the trust dialog: until then, project permissions and the declared
marketplace do not apply.
