"""Shared helpers for the core hooks: event input, settings, git, decisions.

Settings come from three layers, the last one wins:

1. defaults in this file;
2. the plugin options the user set (``CLAUDE_PLUGIN_OPTION_<KEY>``, user-level);
3. the project's ``.claude/working-bee.json`` (committed, per project).

Plugin options are stored in the user's settings, so they cannot hold rules
that only make sense in one repository; the project file can.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_FILE = PurePosixPath(".claude/working-bee.json")

DEFAULTS: dict[str, Any] = {
    "protected_branches": ["main", "master"],
    # files that must not change once they exist on the protected branch
    # (e.g. database migrations already applied in production)
    "frozen_paths": [],
    # edits here always ask the user: they can switch the guards off
    "ask_paths": [
        ".claude/settings*.json",
        ".claude/hooks/**",
        ".claude/working-bee.json",
        ".githooks/**",
        ".git/hooks/**",
    ],
    "brief": {"open_prs": True, "read_first": []},
}


def debug() -> bool:
    """WORKING_BEE_DEBUG=1 makes hooks crash loudly instead of failing open.

    Without it, a hook that crashes looks exactly like one that allowed the
    call. Tests always run with it on.
    """
    return os.environ.get("WORKING_BEE_DEBUG") == "1"


def read_event() -> dict[str, Any]:
    data = json.load(sys.stdin)
    return data if isinstance(data, dict) else {}


def project_root(event: dict[str, Any]) -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd())


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


class ConfigError(ValueError):
    """The project file exists but is not valid; defaults are used instead."""


def load_project_file(root: Path) -> dict[str, Any]:
    path = root / PROJECT_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"{PROJECT_FILE} could not be read: {exc}") from exc
    core = data.get("core", {}) if isinstance(data, dict) else None
    if not isinstance(core, dict):
        raise ConfigError(f'{PROJECT_FILE}: "core" must be an object')
    return core


def settings(root: Path) -> dict[str, Any]:
    """Merged settings. An invalid project file falls back to the other layers."""
    merged = json.loads(json.dumps(DEFAULTS))  # deep copy
    branches = os.environ.get("CLAUDE_PLUGIN_OPTION_PROTECTED_BRANCHES")
    if branches is not None and _csv(branches):
        merged["protected_branches"] = _csv(branches)
    prs = os.environ.get("CLAUDE_PLUGIN_OPTION_BRIEF_OPEN_PRS")
    if prs is not None:
        merged["brief"]["open_prs"] = _bool(prs)
    try:
        project = load_project_file(root)
    except ConfigError:
        project = {}
    for key in ("protected_branches", "frozen_paths"):
        if isinstance(project.get(key), list):
            merged[key] = [str(v) for v in project[key]]
    if isinstance(project.get("ask_paths"), list):  # adds to the defaults
        merged["ask_paths"] += [str(v) for v in project["ask_paths"]]
    if isinstance(project.get("brief"), dict):
        merged["brief"].update(project["brief"])
    return merged


def git(root: Path | str, *args: str, timeout: int = 8) -> str | None:
    """stdout of a git command, or None if git fails or is missing."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def relative(path: str, root: Path) -> PurePosixPath | None:
    """Path relative to the project root, or None if it is outside."""
    try:
        target = Path(path)
        if not target.is_absolute():
            target = root / target
        rel = target.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    return PurePosixPath(rel.as_posix())


def _glob_regex(pattern: str) -> re.Pattern[str]:
    """fnmatch with ``**`` spanning directories and ``*`` staying inside one."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def matches(rel: PurePosixPath, patterns: list[str]) -> str | None:
    """The first pattern that matches the relative path, if any."""
    text = rel.as_posix()
    for pattern in patterns:
        if _glob_regex(pattern).match(text):
            return pattern
    return None


SECRET_NAMES = {".netrc", ".pgpass", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
ENV_TEMPLATES = {"example", "sample", "template", "dist"}


def basename(path: str) -> str:
    """Last part of a path with either separator (Windows paths reach Linux tests too)."""
    return re.split(r"[\\/]", path.rstrip("\\/"))[-1]


def is_secret_file(name: str) -> bool:
    """True for files that hold secrets: .env (not its templates), keys, .netrc."""
    lowered = name.lower()
    if lowered == ".env":
        return True
    if lowered.startswith(".env."):
        return lowered.rsplit(".", 1)[-1] not in ENV_TEMPLATES
    return lowered in SECRET_NAMES or PurePosixPath(lowered).suffix in SECRET_SUFFIXES


def ask(event_name: str, reason: str) -> None:
    """Hand the decision to the user (shown in the permission prompt)."""
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event_name,
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def deny(hook: str, reason: str) -> int:
    """Block the call: exit code 2, and stderr goes back to Claude."""
    print(f"Blocked by working-bee core ({hook}): {reason}", file=sys.stderr)
    return 2
