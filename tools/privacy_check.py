"""Privacy check: keep secrets and private names out of this repository.

Blocks a commit when the staged changes contain:

- secret files (.env, private keys), by path;
- credential patterns (GitHub, Anthropic, OpenAI, AWS, Slack tokens, private keys);
- any term listed in ``.git/info/sensitive-terms``: one term per line, case and
  accent insensitive. That file lives inside ``.git/``, so it is never committed:
  put employer names, internal project names, colleagues and personal e-mails
  there.

Usage:
    python -I tools/privacy_check.py          # staged changes (pre-commit)
    python -I tools/privacy_check.py --all    # every tracked file (CI, audits)

Install the hook once per clone:  git config core.hooksPath .githooks
"""

from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from pathlib import Path

SECRET_PATHS = re.compile(
    r"(^|/)(\.env(\.(?!example$|sample$|template$|dist$)[^/]+)?|id_(rsa|dsa|ecdsa|ed25519)|[^/]+\.(pem|key|p12|pfx))$"
)
CREDENTIALS = re.compile(
    r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-ant-[A-Za-z0-9-]{20,}"
    r"|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|xox[abposr]-[A-Za-z0-9-]{10,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
SELF = "tools/privacy_check.py"  # its own patterns would match


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
    ).stdout


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def load_terms() -> list[str]:
    path = Path(git("rev-parse", "--git-dir").strip()) / "info" / "sensitive-terms"
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [norm(t.strip()) for t in lines if t.strip() and not t.lstrip().startswith("#")]


def staged() -> dict[str, list[str]]:
    """Added lines per staged file."""
    files: dict[str, list[str]] = {}
    current = None
    for line in git("diff", "--cached", "--unified=0", "--no-color", "--diff-filter=ACMR").splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
            if current:
                files[current] = []
        elif current and line.startswith("+") and not line.startswith("+++"):
            files[current].append(line[1:])
    for name in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines():
        files.setdefault(name, [])
    return files


def tracked() -> dict[str, list[str]]:
    files = {}
    for name in git("ls-files").splitlines():
        try:
            files[name] = Path(name).read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            files[name] = []
    return files


def problems(files: dict[str, list[str]], terms: list[str]) -> list[str]:
    found = []
    for name, lines in files.items():
        if SECRET_PATHS.search(name):
            found.append(f"{name}: secret file")
        if name == SELF:
            continue
        for number, line in enumerate(lines, 1):
            if CREDENTIALS.search(line):
                found.append(f"{name}: line {number} looks like a credential")
            low = norm(line)
            for term in terms:
                if term in low:
                    found.append(f"{name}: line {number} has a sensitive term")
    return found


def main() -> int:
    files = tracked() if "--all" in sys.argv else staged()
    found = problems(files, load_terms())
    if not found:
        return 0
    print("privacy check failed (the term itself is not printed):", file=sys.stderr)
    for item in found:
        print(f"  - {item}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
