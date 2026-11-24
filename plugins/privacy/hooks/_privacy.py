"""Shared by the privacy hook and its terms CLI: term lists, detectors, project settings.

Term lists (one term per line, ``#`` comments, case and accent insensitive):

- ``<git common dir>/info/sensitive-terms``: this repository, never committed;
- the personal file: the plugin option ``terms_file`` if set, otherwise
  ``~/.config/working-bee/sensitive-terms.txt`` if it exists.

Detectors find personal data with no list at all. Each one is validated
(check digits) or gated by a label nearby, so that ordinary code rarely
matches. A project allows a detector, or a term it publishes on purpose,
in ``.claude/working-bee.json``::

    {"privacy": {"allow": ["email", "phone"], "allow_terms": ["My Name"]}}

Reading these files is the documented exception to "hooks read only the
event" (ADR 0004).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

MIN_LENGTH = 3  # shorter terms would match almost anything
PERSONAL_DEFAULT = Path("~/.config/working-bee/sensitive-terms.txt")
PROJECT_FILE = Path(".claude") / "working-bee.json"


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True, encoding="utf-8", errors="replace", timeout=20
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


# --- term lists ----------------------------------------------------------------


def repo_terms_file(root: Path) -> Path | None:
    common = git(root, "rev-parse", "--git-common-dir")  # the main .git, also from a worktree
    if not common or not common.strip():
        return None
    return (root / common.strip()).resolve() / "info" / "sensitive-terms"


def personal_terms_file() -> Path:
    option = os.environ.get("CLAUDE_PLUGIN_OPTION_TERMS_FILE", "").strip()
    return Path(option or PERSONAL_DEFAULT).expanduser().resolve()


def term_files(root: Path) -> list[Path]:
    repo = repo_terms_file(root)
    return [p for p in (repo, personal_terms_file()) if p is not None]


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


# --- project settings ----------------------------------------------------------


def project_settings(root: Path) -> dict[str, Any]:
    """The "privacy" object of .claude/working-bee.json; empty if missing or invalid."""
    try:
        data = json.loads((root / PROJECT_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    section = data.get("privacy") if isinstance(data, dict) else None
    return section if isinstance(section, dict) else {}


def _strings(value: Any) -> list[str]:
    return [str(v) for v in value] if isinstance(value, list) else []


def detectors_enabled() -> bool:
    return os.environ.get("CLAUDE_PLUGIN_OPTION_DETECTORS", "true").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


# --- detectors -------------------------------------------------------------------


def _digits(text: str) -> list[int]:
    return [int(ch) for ch in text if ch.isdigit()]


def _check_digit(numbers: list[int], weights: list[int]) -> int:
    rest = sum(n * w for n, w in zip(numbers, weights)) % 11
    return 0 if rest < 2 else 11 - rest


def valid_cpf(text: str) -> bool:
    d = _digits(text)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    first = _check_digit(d[:9], list(range(10, 1, -1)))
    return first == d[9] and _check_digit(d[:10], list(range(11, 1, -1))) == d[10]


def valid_cnpj(text: str) -> bool:
    d = _digits(text)
    if len(d) != 14 or len(set(d)) == 1:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return _check_digit(d[:12], w1) == d[12] and _check_digit(d[:13], [6, *w1]) == d[13]


EMAIL = re.compile(r"(?<![\w.+-])([\w.+-]+)@((?:[\w-]+\.)+[A-Za-z]{2,})(?![\w-])")
SAFE_EMAIL_DOMAINS = re.compile(
    r"(^|\.)(example\.(com|org|net)|example|test|invalid|localhost|users\.noreply\.github\.com)$", re.I
)
SAFE_EMAIL_USERS = {"noreply", "no-reply", "git", "donotreply", "do-not-reply"}
CPF = re.compile(r"(?<![\d.])\d{3}\.\d{3}\.\d{3}-\d{2}(?![\d-])|(?i:\bcpf\b)\D{0,12}(\d{11})(?!\d)")
CNPJ = re.compile(r"(?<![\d.])\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)|(?i:\bcnpj\b)\D{0,12}(\d{14})(?!\d)")
PHONE = re.compile(
    r"(?:\+55[\s-]?\(?\d{2}\)?[\s-]?|\(\d{2}\)\s?)9?\d{4}[\s-]?\d{4}(?!\d)"  # +55 or (DD): no label needed
    r"|(?i:\b(?:tel|telefone|fone|celular|cel|whatsapp|zap|phone)\b)\D{0,6}(\d{2}[\s-]?9?\d{4}[\s-]?\d{4})(?!\d)"
)
CEP = re.compile(r"(?i:\bcep\b)\D{0,4}(\d{5}-?\d{3})(?!\d)")
NAME = r"(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ý][\wÀ-ÿ'.-]+)+"
ADDRESS = re.compile(
    r"\b(?i:rua|avenida|av\.|travessa|alameda|rodovia|estrada|praça|praca|largo)"
    + NAME
    + r",?\s*(?i:n[º°o.]?\s*)?\d+"
    r"|\b(?i:condom[ií]nio|residencial|edif[ií]cio)" + NAME
)
HOST = re.compile(  # not right after a dot or slash: .env.local is a file, not a host
    r"(?<![\w./-])(?:[A-Za-z0-9-]+\.)+(?i:local|internal|corp|intranet|lan|localdomain|home\.arpa)(?![\w-]|\.[\w-])"
)
PRIVATE_IP = re.compile(
    r"(?<![\d.])(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}(?![\d.]|\.\d)"
)


def _all(pattern: re.Pattern[str], text: str) -> list[str]:
    return [m.group(m.lastindex or 0) for m in pattern.finditer(text)]


def find_email(text: str) -> list[str]:
    return [
        m.group(0)
        for m in EMAIL.finditer(text)
        if not SAFE_EMAIL_DOMAINS.search(m.group(2)) and m.group(1).lower() not in SAFE_EMAIL_USERS
    ]


DETECTORS: dict[str, tuple[str, Callable[[str], list[str]]]] = {
    "email": ("an e-mail address", find_email),
    "phone": ("a phone number", lambda t: _all(PHONE, t)),
    "cpf": ("a CPF", lambda t: [v for v in _all(CPF, t) if valid_cpf(v)]),
    "cnpj": ("a CNPJ", lambda t: [v for v in _all(CNPJ, t) if valid_cnpj(v)]),
    "cep": ("a CEP", lambda t: _all(CEP, t)),
    "address": ("a street or building address", lambda t: _all(ADDRESS, t)),
    "host": ("an internal host name", lambda t: _all(HOST, t)),
    "ip": ("a private IP address", lambda t: _all(PRIVATE_IP, t)),
}


# --- scanning --------------------------------------------------------------------


class Scanner:
    """Finds terms and detector matches, minus what this project allows."""

    def __init__(self, root: Path):
        self.files = term_files(root)
        settings = project_settings(root)
        allowed_terms = {norm(t.strip()) for t in _strings(settings.get("allow_terms"))}
        self.terms = [t for t in load_terms(self.files) if t not in allowed_terms]
        allowed = {a.strip().lower() for a in _strings(settings.get("allow"))}
        enabled = detectors_enabled()
        self.detectors = {k: v for k, v in DETECTORS.items() if enabled and k not in allowed}
        self.allowed = sorted(allowed & set(DETECTORS))

    def matches(self, text: str) -> Counter[tuple[str, str]]:
        """(kind, value) -> count. kind is "term" or a detector name."""
        found: Counter[tuple[str, str]] = Counter()
        low = norm(text)
        for term in self.terms:
            if term in low:
                found["term", term] += low.count(term)
        for name, (_, find) in self.detectors.items():
            for value in find(text):
                found[name, value] += 1
        return found

    def added(self, new: str, old: str = "") -> list[tuple[str, str]]:
        """Matches that appear more often in ``new`` than in ``old`` (an edit that keeps one passes)."""
        before = self.matches(old) if old else Counter()
        return [key for key, count in self.matches(new).items() if count > before[key]]


def describe(kind: str, value: str) -> str:
    """How a finding is named in messages: never the value itself."""
    if kind == "term":
        return f"sensitive term {value[0]}***{value[-1]}"
    return DETECTORS[kind][0]
