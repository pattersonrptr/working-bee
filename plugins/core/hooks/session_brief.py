"""SessionStart hook: a short brief, so a new session starts from the facts.

Prints, as context for Claude: the current branch and how many tracked files
changed, the open pull requests (optional, needs ``gh``), the files the project
asks to read first, and a warning when ``.claude/working-bee.json`` is invalid.
Each line is optional: a missing tool just leaves its line out.

Always exits 0: a brief must never stop a session from starting.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

PR_TEMPLATE = '{{range .}}#{{.number}} {{.title}} ({{.headRefName}}){{"\\n"}}{{end}}'


def open_prs(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--limit", "10",
             "--json", "number,title,headRefName", "--template", PR_TEMPLATE],
            cwd=str(root), capture_output=True, encoding="utf-8",
            errors="replace", timeout=8,
        )  # fmt: skip
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return "; ".join(result.stdout.strip().splitlines()) or "none"


def brief(root: Path) -> list[str]:
    lines = ["Session brief (working-bee core):"]
    branch = c.git(root, "branch", "--show-current")
    if branch is not None:
        changed = c.git(root, "status", "--short", "--untracked-files=no") or ""
        count = len(changed.splitlines())
        protected = c.settings(root)["protected_branches"]
        note = " (protected: work on a feature branch)" if branch in protected else ""
        lines.append(f"- Branch: {branch or '(detached)'}{note}; {count} changed tracked file(s)")
    try:
        c.load_project_file(root)
    except c.ConfigError as exc:
        lines.append(f"- WARNING: {exc}. Using defaults; tell the user.")
    conf = c.settings(root)
    if branch is not None and conf["brief"].get("open_prs"):
        prs = open_prs(root)
        if prs is not None:
            lines.append(f"- Open PRs: {prs}")
    read_first = [p for p in conf["brief"].get("read_first", []) if (root / p).exists()]
    if read_first:
        lines.append("- Read before planning: " + ", ".join(read_first))
    return lines


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows defaults to cp1252
    event = c.read_event()
    lines = brief(c.project_root(event))
    if len(lines) > 1:
        print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never block a session start
        if c.debug():
            raise
