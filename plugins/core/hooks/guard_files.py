"""PreToolUse hook for file tools (Read, Grep, Edit, Write, MultiEdit, NotebookEdit).

- Secret files (``.env``, private keys, ``.netrc``...) are neither read nor
  written, wherever they are: once a secret is in the context it can end up in
  a transcript, a commit or a log. Templates such as ``.env.example`` are fine.
- ``frozen_paths`` (project setting) cannot be edited once they exist on the
  protected branch: e.g. a migration production may have applied already.
- ``ask_paths`` (Claude's own settings and hooks, git hooks...) are not
  blocked, but every edit asks the user, so the agent cannot quietly switch its
  guards off.

Exit 2 blocks and tells Claude why. Any unexpected error lets the call through
(fail-open), so a hook bug never stops work.
"""

from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

HOOK = "guard_files"
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def target_path(tool: str, tool_input: dict) -> str | None:
    if tool == "NotebookEdit":
        return tool_input.get("notebook_path")
    if tool == "Grep":
        return tool_input.get("path")
    return tool_input.get("file_path")


def on_branch(root: Path, branch: str, rel: PurePosixPath) -> bool:
    return c.git(root, "cat-file", "-e", f"{branch}:{rel.as_posix()}") is not None


def decide(event: dict) -> tuple[str, str] | None:
    """("deny" | "ask", reason) or None to let the call through."""
    tool = event.get("tool_name", "")
    path = target_path(tool, event.get("tool_input") or {})
    if not path:
        return None
    name = c.basename(path)
    if c.is_secret_file(name):
        verb = "edited" if tool in WRITE_TOOLS else "read"
        return "deny", (
            f"{name} holds secrets and is not {verb} by Claude. Ask the user to "
            "handle it, or work with a template such as .env.example."
        )
    if tool not in WRITE_TOOLS:
        return None
    root = c.project_root(event)
    rel = c.relative(path, root)
    if rel is None:
        return None  # outside the project: only the secret rule applies
    conf = c.settings(root)
    frozen = c.matches(rel, conf["frozen_paths"])
    if frozen:
        for branch in conf["protected_branches"]:
            if on_branch(root, branch, rel):
                return "deny", (
                    f"{rel} is already on {branch} and matches the frozen pattern "
                    f"'{frozen}'. Add a new file (e.g. a new migration) instead "
                    "of changing this one."
                )
    if c.matches(rel, conf["ask_paths"]):
        return "ask", f"{rel} configures Claude's own guardrails; confirm this change."
    return None


def main() -> int:
    try:
        event = c.read_event()
        decision = decide(event)
    except Exception:  # fail-open: a broken hook must not stop work
        if c.debug():
            raise
        return 0
    if decision is None:
        return 0
    kind, reason = decision
    if kind == "ask":
        c.ask("PreToolUse", reason)
        return 0
    return c.deny(HOOK, reason)


if __name__ == "__main__":
    sys.exit(main())
