"""Manage the sensitive-term lists without ever printing them (used by /privacy:terms).

    python terms_cli.py add [--repo] TERM...    append terms (personal list by default)
    python terms_cli.py check TEXT...           say, for each text, whether a term already covers it
    python terms_cli.py count                   how many terms each list holds

Run from the project folder. The personal list is the plugin option
``terms_file`` when the environment has it (hooks do; the Bash tool does not),
otherwise ``~/.config/working-bee/sensitive-terms.txt``, which ``add``
creates. ``--file PATH`` overrides it.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _privacy as p  # noqa: E402

HEADER = "# working-bee privacy: one sensitive term per line. Never commit this file.\n"


def target(args: argparse.Namespace, root: Path) -> Path | None:
    if args.repo:
        return p.repo_terms_file(root)
    return Path(args.file).expanduser().resolve() if args.file else p.personal_terms_file()


def add(args: argparse.Namespace, root: Path) -> int:
    path = target(args, root)
    if path is None:
        print("not a git repository: use the personal list (drop --repo)", file=sys.stderr)
        return 1
    known = set(p.load_terms([path]))
    new = []
    for raw in args.terms:
        term = raw.strip()
        if len(p.norm(term)) < p.MIN_LENGTH:
            print(f"skipped a term shorter than {p.MIN_LENGTH} characters")
        elif p.norm(term) in known or p.norm(term) in {p.norm(t) for t in new}:
            print(f"already listed: {p.describe('term', p.norm(term))}")
        else:
            new.append(term)
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        prefix = "" if path.is_file() and path.stat().st_size else HEADER
        if path.is_file() and path.stat().st_size and not path.read_bytes().endswith(b"\n"):
            prefix = "\n"
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(prefix + "".join(f"{t}\n" for t in new))
        scope = "this repository" if args.repo else "every project (personal list)"
        for term in new:
            print(f"added {p.describe('term', p.norm(term))} for {scope}")
    return 0


def check(args: argparse.Namespace, root: Path) -> int:
    terms = p.load_terms(p.term_files(root))
    for text in args.texts:
        low = p.norm(text)
        covered = any(t in low for t in terms)
        print(
            f"{'covered' if covered else 'not covered'}: {p.describe('term', low) if len(low) >= 2 else '?'}"
        )
    return 0


def count(_: argparse.Namespace, root: Path) -> int:
    repo = p.repo_terms_file(root)
    print(f"this repository: {len(p.load_terms([repo])) if repo else 0} term(s)")
    print(f"personal: {len(p.load_terms([p.personal_terms_file()]))} term(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("add")
    a.add_argument("--repo", action="store_true", help="this repository's list instead of the personal one")
    a.add_argument("--file", help="personal list path, if not the default")
    a.add_argument("terms", nargs="+")
    c = sub.add_parser("check")
    c.add_argument("texts", nargs="+")
    sub.add_parser("count")
    args = parser.parse_args(argv)
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    return {"add": add, "check": check, "count": count}[args.command](args, root)


if __name__ == "__main__":
    sys.exit(main())
