"""Keep sensitive terms and personal data out of files, commits, pushes and published text.

What counts as sensitive: the term lists and the detectors in ``_privacy.py``
(names the user listed; e-mails, phones, CPF, CNPJ, CEP, addresses, internal
hosts and private IPs found with no list).

The guard **asks** instead of blocking: the permission prompt shows what was
found (masked), and only the user can approve it. "The secret is not the name,
it is the approval": a public resume may name an employer; an internal
codename should never leave without someone saying yes. A repository that
publishes some of it on purpose allows it in ``.claude/working-bee.json``,
which is reviewed like code and whose edits always ask.

Events:

- PreToolUse on Write/Edit/MultiEdit/NotebookEdit: text that adds a finding
  (an edit that keeps one already there passes, so old files stay editable).
- PreToolUse on Bash/PowerShell: ``git commit`` checks the staged changes
  (``-a`` adds the tracked ones) and the command, which holds the message;
  ``git push`` checks the commits on no remote yet; ``gh``, ``curl`` and
  ``wget`` check the command text, which is what they would publish.
- SessionStart: how many terms are loaded and which detectors are on, never
  which terms.

Without a person to ask (``claude -p``), "ask" means the call does not run.
Any unexpected error lets the call through (fail-open); ``WORKING_BEE_DEBUG=1``
re-raises.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _privacy as p  # noqa: E402

HOOK = "privacy"
MAX_FINDINGS = 8
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
GIT_CALL = re.compile(r"\bgit\b[^;&|\n]*?\s(commit|push)\b")
COMMIT_ALL = re.compile(r"\s(--all|-[a-zA-Z]*a[a-zA-Z]*)\b")
PUBLISHERS = re.compile(r"(^|[;&|\s(])(gh|curl|wget|Invoke-WebRequest|Invoke-RestMethod)\s", re.I)
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")

Finding = tuple[str, str, str]  # (kind, value, where)


def debug() -> bool:
    return os.environ.get("WORKING_BEE_DEBUG") == "1"


def line_of(text: str, kind: str, value: str) -> int:
    for number, line in enumerate(text.splitlines(), 1):
        if (p.norm(value) in p.norm(line)) if kind == "term" else (value in line):
            return number
    return 1


def diff_findings(diff: str, scan: p.Scanner) -> list[Finding]:
    """Findings on the added lines of a unified diff, with path:line."""
    out: list[Finding] = []
    path, number = None, 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif hunk := HUNK.match(line):
            number = int(hunk.group(1))
        elif line.startswith("+") and path:
            out += [(kind, value, f"{path}:{number}") for kind, value in scan.matches(line[1:])]
            number += 1
        elif line.startswith(" "):
            number += 1
    return out


def check_write(event: dict[str, Any], root: Path, scan: p.Scanner) -> list[Finding]:
    data = event.get("tool_input") or {}
    raw = str(data.get("file_path") or data.get("notebook_path") or "")
    if raw:
        target = Path(raw) if Path(raw).is_absolute() else root / raw
        if target.resolve() in scan.files:
            return []  # editing a term list itself
    try:
        where = Path(raw).resolve().relative_to(root.resolve()).as_posix() if raw else "the file"
    except ValueError:
        where = raw
    out = [(kind, value, f"{where} (its path)") for kind, value in scan.matches(raw) if kind == "term"]
    tool = event.get("tool_name")
    if tool == "Write":
        content = str(data.get("content") or "")
        out += [(k, v, f"{where}:{line_of(content, k, v)}") for k, v in scan.added(content)]
    elif tool == "Edit":
        new, old = str(data.get("new_string") or ""), str(data.get("old_string") or "")
        out += [(k, v, where) for k, v in scan.added(new, old)]
    elif tool == "MultiEdit":
        for edit in data.get("edits") or []:
            if isinstance(edit, dict):
                new, old = str(edit.get("new_string") or ""), str(edit.get("old_string") or "")
                out += [(k, v, where) for k, v in scan.added(new, old)]
    elif tool == "NotebookEdit":
        out += [(k, v, where) for k, v in scan.added(str(data.get("new_source") or ""))]
    return out


def check_command(event: dict[str, Any], root: Path, scan: p.Scanner) -> list[Finding]:
    command = str((event.get("tool_input") or {}).get("command") or "")
    out: list[Finding] = []
    calls = {m.group(1) for m in GIT_CALL.finditer(command)}
    if calls or PUBLISHERS.search(command):
        out += [(kind, value, "the command text") for kind, value in scan.matches(command)]
    if "commit" in calls:
        diff = p.git(root, "diff", "--cached", "-U0", "--no-color", "--no-ext-diff") or ""
        if COMMIT_ALL.search(command):
            diff += p.git(root, "diff", "-U0", "--no-color", "--no-ext-diff") or ""
        out += diff_findings(diff, scan)
    if "push" in calls:
        unpushed = ("log", "HEAD", "--not", "--remotes", "--no-color", "--no-ext-diff")
        messages = p.git(root, *unpushed, "--format=%h %B") or ""
        out += [(k, v, "a commit message not pushed yet") for k, v in scan.matches(messages)]
        out += diff_findings(p.git(root, *unpushed, "-p", "-U0", "--format=") or "", scan)
    return out


def safe(where: str, scan: p.Scanner) -> str:
    """A location for the message, hidden when it holds a finding itself (a path such as docs/<term>/)."""
    return "a path that holds sensitive data" if scan.matches(where) else where


def reason(findings: list[Finding], scan: p.Scanner) -> str:
    listed = sorted({f"{p.describe(kind, value)} in {safe(where, scan)}" for kind, value, where in findings})
    more = f" (and {len(listed) - MAX_FINDINGS} more)" if len(listed) > MAX_FINDINGS else ""
    return (
        f"working-bee privacy found {'; '.join(listed[:MAX_FINDINGS])}{more}. Approve only if this is meant to "
        "be shared. Otherwise remove or generalize it ('the employer', 'a client', 'user@example.com')."
    )


def brief(scan: p.Scanner) -> str:
    on = ", ".join(scan.detectors) or "none"
    allowed = f"; allowed in this project: {', '.join(scan.allowed)}" if scan.allowed else ""
    terms = f"{len(scan.terms)} sensitive term(s) loaded" if scan.terms else "no sensitive terms configured"
    return f"privacy: {terms}; detectors: {on}{allowed}. Findings in files, commits and pushes ask the user."


def main() -> int:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            return 0
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd())
        scan = p.Scanner(root)
        if event.get("hook_event_name") == "SessionStart":
            print(brief(scan))
            return 0
        if not scan.terms and not scan.detectors:
            return 0
        tool = event.get("tool_name")
        if tool in WRITE_TOOLS:
            findings = check_write(event, root, scan)
        elif tool in SHELL_TOOLS:
            findings = check_command(event, root, scan)
        else:
            return 0
        if findings:
            decision = {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": reason(findings, scan),
            }
            print(json.dumps({"hookSpecificOutput": decision}))
        return 0
    except Exception:
        if debug():
            raise
        return 0


if __name__ == "__main__":
    sys.exit(main())
