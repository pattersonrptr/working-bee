---
name: learn
description: Turns a mistake into a one-line rule in the project's AGENTS.md (or CLAUDE.md), so the same mistake is not repeated in later sessions. Use when the user corrects you ("no, we don't do that", "you did X again", "remember this"), when you notice your own mistake was caused by a missing project rule, or when the user runs /learn.
argument-hint: "[what went wrong, or empty to use the last correction]"
allowed-tools: Read, Grep, Glob, Edit, Bash(git log:*), Bash(git diff:*)
---

# Learn from a mistake

Input: `$ARGUMENTS`. If empty, use the most recent correction in this conversation. If there is none, ask what went wrong; do not invent one.

## 1. Understand it

State in one sentence each: **what happened**, **what should have happened**, and **why it happened**: a missing rule, a rule that was unclear, or a rule that exists but was ignored. Ask the user if you cannot tell.

- Rule exists and is clear but was ignored → do not add a duplicate. Make the existing rule more prominent or concrete, or suggest a hook (step 3).
- Not a project rule, but a fact about a tool, library or platform → that is a gotcha: use `/memory:gotcha` instead.

## 2. Write the rule

One line, imperative, specific enough to check, with the reason when it is not obvious:

- Good: `Run backend tests with \`poetry run pytest src/tests\`, never \`pytest\` from the repo root (it picks up the scrapers' conftest).`
- Bad: `Be careful with tests.` (not checkable) · `Never make mistakes with dates.` (no action)

Rules: [references/rule-style.md](references/rule-style.md) for wording, placement and examples. Read it the first time in a session.

## 3. Choose where it goes

1. Read `.claude/working-bee.json` if it exists: `memory.target` names the file (default: `AGENTS.md`; if the project only has `CLAUDE.md`, use it).
2. Personal habits that apply to every project (language, tone, tools you prefer) go to `~/.claude/CLAUDE.md` instead: ask before writing there.
3. In the file, put the rule under the matching section: `Always`, `Ask first`, `Never`, or the section about the area it concerns (commands, tests, known traps). Create the section only if none fits.
4. **Expensive or irreversible mistakes** (lost data, pushed secrets, broken production): say that a rule can be ignored and propose a guard as well, for example `frozen_paths` or `ask_paths` in `.claude/working-bee.json` (working-bee core) or a permission rule.

## 4. Confirm, then write

Show the user the exact line and where it goes (file and section). Search the file for rules that overlap (`Grep` for its key words) and say if this one replaces or merges with one. Write only after the user agrees. Then reply in one line: the rule and the file.
