---
name: test
description: Runs the project's Python tests with its own runner (uv, poetry, a .venv or plain python), the narrowest relevant tests first and then the whole suite, and reports failures briefly with their cause. Use when Python code changed and needs checking, before a commit or a pull request, when the user asks to run the tests, or when the user runs /test.
argument-hint: "[test path, node id or -k expression; empty for the tests related to the change]"
allowed-tools: Bash, PowerShell, Read, Grep, Glob
---

# Run the Python tests

Input: `$ARGUMENTS`. If empty, start from the tests related to what changed in this conversation (or in `git diff`).

## 1. Find the command

The project's own instructions win: if `AGENTS.md`, `CLAUDE.md`, a `Makefile` or `pyproject.toml` scripts name a
test command, use it. Otherwise, the first that applies:

| Found in the project root | Command |
|---|---|
| `uv.lock` | `uv run pytest` |
| `poetry.lock` | `poetry run pytest` |
| `.venv/` | `.venv/bin/python -m pytest` (Windows: `.venv\Scripts\python -m pytest`) |
| anything else | `python -m pytest` |

Never install or sync dependencies to make tests run without asking the user first.

## 2. Narrow, then wide

1. Run the tests closest to the change (`tests/test_<module>.py`, a node id, or `-k`), with `-q`.
2. If they pass, run the whole suite with `-q`. Add `-x` only when the suite is slow.
3. A failure: read the traceback, find the cause, and say which side is wrong: the code or the test.

## 3. Rules

- Never weaken, skip or delete a test to make it pass. A test that is truly wrong is changed only after saying why.
- A flaky test (passes on a rerun with no change) is reported as flaky, not as fixed.
- Report in a few lines: command, passed/failed counts, and for each failure the test id and its cause.
