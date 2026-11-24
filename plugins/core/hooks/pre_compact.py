"""PreCompact hook: tell the summarizer which git facts to keep.

Compaction rewrites the conversation into a summary, and details such as the
branch, uncommitted files and recent commits get lost. Whatever this hook
prints becomes extra instructions for that summary (Claude Code caps it at
10,000 characters).

Always exits 0: it must never block a compaction.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

MAX_FILES = 30
MAX_CHARS = 8000


def instructions(root: Path) -> str | None:
    branch = c.git(root, "branch", "--show-current")
    if branch is None:
        return None  # not a git repository
    status = (c.git(root, "status", "--short") or "").splitlines()
    commits = c.git(root, "log", "--oneline", "-5") or "(no commits)"
    shown = "\n".join(status[:MAX_FILES]) or "(clean)"
    if len(status) > MAX_FILES:
        shown += f"\n... and {len(status) - MAX_FILES} more"
    text = (
        "Keep these git facts in the summary, verbatim where possible:\n"
        f"- Current branch: {branch or '(detached HEAD)'}\n"
        f"- Uncommitted changes:\n{shown}\n"
        f"- Last commits:\n{commits}\n"
        "Also keep: the task in progress, decisions the user made, and what was "
        "verified versus only assumed."
    )
    return text[:MAX_CHARS]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    event = c.read_event()
    text = instructions(c.project_root(event))
    if text:
        print(text)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never block a compaction
        if c.debug():
            raise
