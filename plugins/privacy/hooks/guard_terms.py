"""Keep sensitive terms (employer, clients, colleagues, private projects) out of files, commits and pushes.

Terms come from two plain-text files, one term per line, ``#`` for comments,
matched case and accent insensitively as substrings:

- ``.git/info/sensitive-terms`` of the project: inside ``.git/``, so it is never
  committed (the same file ``tools/privacy_check.py`` reads);
- the personal file set in the plugin option ``terms_file``, for terms that
  apply to every project.

This is the one documented exception to "hooks read only the event JSON"
(ADR 0004): the list cannot be in the event, and must not be in the repository.

Events:

- PreToolUse on Write/Edit/MultiEdit/NotebookEdit: blocks text that adds a term
  (an edit that keeps a term already there passes, so old files stay editable).
- PreToolUse on Bash/PowerShell: ``git commit`` checks the staged changes
  (``-a`` adds the tracked ones) and the command itself; ``git push`` checks
  the commits that are on no remote yet; ``gh``, ``curl`` and ``wget`` check the
  command text, which is what they would publish.
- SessionStart: says how many terms are loaded, never which.

Messages mask the term (``a***z``). Exit 2 blocks and tells Claude why. Any
unexpected error lets the call through (fail-open); ``WORKING_BEE_DEBUG=1``
re-raises.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

HOOK = "guard_terms"
MIN_LENGTH = 3  # shorter terms would match almost anything
MAX_FINDINGS = 8
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
GIT_CALL = re.compile(r"\bgit\b[^;&|\n]*?\s(commit|push)\b")
COMMIT_ALL = re.compile(r"\s(--all|-[a-zA-Z]*a[a-zA-Z]*)\b")
PUBLISHERS = re.compile(r"(^|[;&|\s(])(gh|curl|wget|Invoke-WebRequest|Invoke-RestMethod)\s", re.I)
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")


def debug() -> bool:
    return os.environ.get("WORKING_BEE_DEBUG") == "1"


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def mask(term: str) -> str:
    return f"{term[0]}***{term[-1]}"


def safe(where: str, terms: list[str]) -> str:
    """A location for the message, hidden when it holds a term itself (a path such as docs/<term>/)."""
    return "a path that holds a sensitive term" if found_in(where, terms) else where


def git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True, encoding="utf-8", errors="replace", timeout=20
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def term_files(root: Path) -> list[Path]:
    files = []
    common = git(root, "rev-parse", "--git-common-dir")  # the main .git, also from a worktree
    if common and common.strip():
        files.append((root / common.strip()).resolve() / "info" / "sensitive-terms")
    personal = os.environ.get("CLAUDE_PLUGIN_OPTION_TERMS_FILE", "").strip()
    if personal:
        files.append(Path(personal).expanduser().resolve())
    return files


def load_terms(files: list[Path]) -> list[str]:
    terms: list[str] = []
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            term = norm(line.strip())
            if len(term) >= MIN_LENGTH and not term.startswith("#") and term not in terms:
                terms.append(term)
    return terms


def found_in(text: str, terms: list[str]) -> list[str]:
    low = norm(text)
    return [t for t in terms if t in low]


def added(new: str, old: str, terms: list[str]) -> list[str]:
    """Terms that appear more often in ``new`` than in ``old``."""
    low_new, low_old = norm(new), norm(old)
    return [t for t in terms if low_new.count(t) > low_old.count(t)]


def line_of(text: str, term: str) -> int:
    for number, line in enumerate(text.splitlines(), 1):
        if term in norm(line):
            return number
    return 1


def diff_findings(diff: str, terms: list[str]) -> list[tuple[str, str]]:
    """(term, "path:line") for each added line of a unified diff with a term."""
    out: list[tuple[str, str]] = []
    path, number = None, 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif hunk := HUNK.match(line):
            number = int(hunk.group(1))
        elif line.startswith("+") and path:
            out += [(t, f"{path}:{number}") for t in found_in(line[1:], terms)]
            number += 1
        elif line.startswith(" "):
            number += 1
    return out


def check_write(
    event: dict[str, Any], root: Path, terms: list[str], files: list[Path]
) -> list[tuple[str, str]]:
    data = event.get("tool_input") or {}
    raw = data.get("file_path") or data.get("notebook_path") or ""
    if raw:
        target = Path(raw) if Path(raw).is_absolute() else root / raw
        if target.resolve() in files:
            return []  # editing the list itself
    try:
        where = Path(raw).resolve().relative_to(root.resolve()).as_posix() if raw else "the file"
    except ValueError:
        where = raw
    out = [(t, f"{where} (its path)") for t in found_in(raw, terms)]
    tool = event.get("tool_name")
    if tool == "Write":
        content = str(data.get("content") or "")
        out += [(t, f"{where}:{line_of(content, t)}") for t in found_in(content, terms)]
    elif tool == "Edit":
        new = str(data.get("new_string") or "")
        out += [(t, where) for t in added(new, str(data.get("old_string") or ""), terms)]
    elif tool == "MultiEdit":
        for edit in data.get("edits") or []:
            if isinstance(edit, dict):
                new, old = str(edit.get("new_string") or ""), str(edit.get("old_string") or "")
                out += [(t, where) for t in added(new, old, terms)]
    elif tool == "NotebookEdit":
        out += [(t, where) for t in found_in(str(data.get("new_source") or ""), terms)]
    return out


def check_command(event: dict[str, Any], root: Path, terms: list[str]) -> list[tuple[str, str]]:
    command = str((event.get("tool_input") or {}).get("command") or "")
    out: list[tuple[str, str]] = []
    calls = {m.group(1) for m in GIT_CALL.finditer(command)}
    if calls or PUBLISHERS.search(command):
        out += [(t, "the command text") for t in found_in(command, terms)]
    if "commit" in calls:
        diff = git(root, "diff", "--cached", "-U0", "--no-color", "--no-ext-diff") or ""
        if COMMIT_ALL.search(command):
            diff += git(root, "diff", "-U0", "--no-color", "--no-ext-diff") or ""
        out += diff_findings(diff, terms)
    if "push" in calls:
        unpushed = ("log", "HEAD", "--not", "--remotes", "--no-color", "--no-ext-diff")
        messages = git(root, *unpushed, "--format=%h %B") or ""
        out += [(t, "a commit message not pushed yet") for t in found_in(messages, terms)]
        out += diff_findings(git(root, *unpushed, "-p", "-U0", "--format=") or "", terms)
    return out


def brief(terms: list[str], files: list[Path]) -> str:
    if terms:
        return f"privacy: {len(terms)} sensitive term(s) loaded; files, commits and pushes are checked."
    where = " and ".join(str(f) for f in files) or ".git/info/sensitive-terms"
    return f"privacy: no sensitive terms configured ({where}), so nothing is being checked."


def main() -> int:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            return 0
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd())
        files = term_files(root)
        terms = load_terms(files)
        if event.get("hook_event_name") == "SessionStart":
            print(brief(terms, files))
            return 0
        if not terms:
            return 0
        tool = event.get("tool_name")
        if tool in WRITE_TOOLS:
            findings = check_write(event, root, terms, files)
        elif tool in SHELL_TOOLS:
            findings = check_command(event, root, terms)
        else:
            return 0
        if not findings:
            return 0
        listed = sorted({f"{mask(t)} in {safe(where, terms)}" for t, where in findings})
        more = f" (and {len(listed) - MAX_FINDINGS} more)" if len(listed) > MAX_FINDINGS else ""
        print(
            f"Blocked by working-bee privacy ({HOOK}): sensitive term "
            + "; ".join(listed[:MAX_FINDINGS])
            + f"{more}. Remove or generalize it (for example 'the employer', 'a client'). "
            "The list lives outside the repository; do not read or print it.",
            file=sys.stderr,
        )
        return 2
    except Exception:
        if debug():
            raise
        return 0


if __name__ == "__main__":
    sys.exit(main())
