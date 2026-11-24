"""PreToolUse hook for shell commands (Bash and PowerShell tools).

Denies (exit 2, Claude reads why):

- ``git commit`` on a protected branch, and ``git push`` to one (explicit
  refspec, deletion, or a bare push from it);
- force pushes to a protected branch, and ``git push --mirror``;
- ``--no-verify`` (and ``git commit -n``), which skips the git hooks;
- ``gh pr merge --admin``, which bypasses branch protection;
- recursive deletes of a root, the home folder or the whole working directory;
- printing secret files (``cat .env``) and staging them (``git add .env``).

Asks the user: force pushes to other branches, ``git push --all``,
``git reset --hard`` and ``git clean -f``: legitimate, but they destroy work.

Branch protection on the git host is the real lock; this hook stops Claude
earlier, with a clear message. The command parsing is a heuristic: it reads
each segment of a chain (``&&``, ``||``, ``;``, ``|``, new lines) on its own.
Any unexpected error lets the call through (fail-open).
"""

from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

HOOK = "guard_commands"
SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|\n]")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
PREFIXES = {"sudo", "command", "env", "time", "nohup", "&"}
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}

RM_COMMANDS = {"rm", "remove-item", "ri", "del", "erase", "rd", "rmdir"}
READERS = {
    "cat", "type", "head", "tail", "less", "more", "bat", "nl", "strings",
    "xxd", "od", "base64", "grep", "egrep", "rg", "findstr",
    "get-content", "gc", "select-string", "sls",
}  # fmt: skip
DANGEROUS_TARGETS = {"/", "~", "$home", "${home}", "$env:userprofile", ".", "..", "*", ""}
DRIVE_ROOT = re.compile(r"^(?:[a-z]:|/[a-z])$")  # C: (Windows) or /c (Git Bash)

Decision = tuple[str, str]  # ("deny" | "ask", reason)


def words(segment: str) -> list[str]:
    # Backslashes become slashes so Windows paths survive POSIX quoting rules.
    text = segment.replace("\\", "/")
    try:
        tokens = shlex.split(text, posix=True)
    except ValueError:
        tokens = text.split()
    while tokens and (ASSIGNMENT.match(tokens[0]) or tokens[0].lower() in PREFIXES):
        tokens = tokens[1:]
    return tokens


def git_call(tokens: list[str], cwd: Path) -> tuple[str, list[str], Path] | None:
    """(subcommand, its arguments, directory it runs in) for a git call."""
    if not tokens or tokens[0].lower() not in ("git", "git.exe"):
        return None
    i, where = 1, cwd
    while i < len(tokens) and tokens[i].startswith("-"):
        if tokens[i] == "-C" and i + 1 < len(tokens):
            where = cwd / tokens[i + 1]
        i += 2 if tokens[i] in GIT_OPTS_WITH_VALUE else 1
    if i >= len(tokens):
        return None
    return tokens[i], tokens[i + 1 :], where


def branch_name(refspec: str) -> str:
    dest = refspec.lstrip("+").split(":")[-1]
    return dest[len("refs/heads/") :] if dest.startswith("refs/heads/") else dest


def check_push(args: list[str], branch: str | None, protected: list[str]) -> Decision | None:
    force = any(a in ("--force", "-f") or a.startswith("--force-with-lease") for a in args)
    if "--mirror" in args:
        return "deny", "git push --mirror rewrites every branch on the remote"
    refspecs = [a for a in args if not a.startswith("-")][1:]  # first one is the remote
    targets = {branch_name(r) for r in refspecs} if refspecs else {branch}
    hits = sorted(t for t in targets if t in protected)
    if hits:
        if force or any(r.startswith("+") for r in refspecs):
            return "deny", f"force push to protected branch {hits[0]}"
        if refspecs:
            return "deny", f"pushing to protected branch {hits[0]}; open a pull request"
        return "deny", f"you are on protected branch {hits[0]}; push a feature branch"
    if force or any(r.startswith("+") for r in refspecs):
        return "ask", "force push rewrites history on the remote"
    if "--all" in args:
        return "ask", "git push --all pushes every local branch"
    return None


def check_git(sub: str, args: list[str], branch: str | None, protected: list[str]) -> Decision | None:
    if "--no-verify" in args or (sub == "commit" and "-n" in args):
        return "deny", "--no-verify skips the git hooks (pre-commit checks)"
    if sub == "add" and any(c.is_secret_file(c.basename(a)) for a in args):
        return "deny", "staging a secret file; keep it out of git (.gitignore)"
    if sub == "commit" and branch in protected:
        return "deny", f"you are on protected branch {branch}; create a branch first"
    if sub == "push":
        return check_push(args, branch, protected)
    if sub == "reset" and "--hard" in args:
        return "ask", "git reset --hard discards uncommitted work"
    if sub == "clean" and any(a.startswith("-") and "f" in a.lstrip("-") for a in args):
        return "ask", "git clean -f deletes untracked files"
    return None


def is_dangerous_target(arg: str) -> bool:
    target = arg.strip("'\"").lower().rstrip("*").rstrip("/") or "/"
    if arg.strip("'\"") in ("*", "./*", "~/*", "/*"):
        return True
    return target in DANGEROUS_TARGETS or bool(DRIVE_ROOT.match(target))


def check_rm(tokens: list[str]) -> Decision | None:
    flags = [t.lower() for t in tokens[1:] if t.startswith("-")]
    recursive = any(
        f in ("--recursive", "-recurse", "-r") or (not f.startswith("--") and "r" in f[1:]) for f in flags
    )
    if not recursive and tokens[0].lower() not in ("rd", "rmdir"):
        return None
    targets = [t for t in tokens[1:] if not t.startswith("-")]
    for target in targets:
        if is_dangerous_target(target):
            return "deny", f"recursive delete of '{target}' (a root, home or the whole folder)"
    return None


def decide(event: dict) -> Decision | None:
    command = (event.get("tool_input") or {}).get("command")
    if not command:
        return None
    root = c.project_root(event)
    cwd = Path(event.get("cwd") or root)
    protected = c.settings(root)["protected_branches"]
    asked: Decision | None = None
    branch: str | None = None
    branch_known = False
    for segment in SEGMENT_SPLIT.split(command):
        tokens = words(segment.strip())
        if not tokens:
            continue
        name = tokens[0].lower()
        decision: Decision | None = None
        if tokens[:3] == ["gh", "pr", "merge"] and "--admin" in tokens:
            decision = "deny", "gh pr merge --admin bypasses branch protection"
        elif name in RM_COMMANDS:
            decision = check_rm(tokens)
        elif name in READERS and any(c.is_secret_file(c.basename(t)) for t in tokens[1:]):
            decision = "deny", "printing a secret file would put it in the conversation"
        else:
            call = git_call(tokens, cwd)
            if call is None:
                continue  # not a command we judge (or a line of a commit message)
            sub, args, where = call
            if sub in ("switch", "checkout"):
                branch, branch_known = None, True  # the branch changes mid-command
                continue
            if sub in ("commit", "push") and not branch_known:
                branch, branch_known = c.git(where, "branch", "--show-current"), True
            decision = check_git(sub, args, branch, protected)
        if decision and decision[0] == "deny":
            return decision
        asked = asked or decision
    return asked


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
    return c.deny(HOOK, reason + ".")


if __name__ == "__main__":
    sys.exit(main())
