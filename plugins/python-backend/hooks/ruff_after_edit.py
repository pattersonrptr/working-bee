"""PostToolUse hook for Edit and Write: ruff fixes and formats the Python file just changed.

1. ``ruff check --fix`` on the file, then ``ruff format``, from the project
   root, so the project's own ruff configuration (pyproject.toml, ruff.toml)
   applies. ``--force-exclude`` keeps excluded paths excluded.
2. Problems ruff cannot fix are handed back to Claude next to the tool result
   (``"decision": "block"``), so it fixes them while the file is still fresh.
3. If ruff cannot be found, Claude is told once per session, not on every edit.

Which ruff runs ("runner"): ``auto`` tries the project's ``.venv``, then
``poetry run`` when there is a ``poetry.lock``, then ``ruff`` on PATH. ``uv``,
``poetry`` and ``path`` force one of them. Never ``uvx``: no network calls.

Settings, last layer wins: defaults; the plugin option ``runner``; the
``"python-backend"`` object in the project's ``.claude/working-bee.json``.

The tool already ran, so this hook never blocks anything. Any unexpected error
is ignored (fail-open); ``WORKING_BEE_DEBUG=1`` re-raises.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PLUGIN = "python-backend"
PROJECT_FILE = Path(".claude") / "working-bee.json"
DEFAULTS: dict[str, Any] = {"runner": "auto", "fix": True, "format": True, "report": True}
RUNNERS = {"auto", "venv", "uv", "poetry", "path"}
PY_SUFFIXES = {".py", ".pyi"}
MAX_LINES = 20
TIMEOUT = 25


def debug() -> bool:
    return os.environ.get("WORKING_BEE_DEBUG") == "1"


def settings(root: Path) -> dict[str, Any]:
    merged = dict(DEFAULTS)
    option = os.environ.get("CLAUDE_PLUGIN_OPTION_RUNNER", "").strip().lower()
    if option in RUNNERS:
        merged["runner"] = option
    try:
        data = json.loads((root / PROJECT_FILE).read_text(encoding="utf-8"))
        project = data.get(PLUGIN, {}) if isinstance(data, dict) else {}
    except (OSError, ValueError):
        project = {}  # missing or invalid: core's session brief reports invalid files
    if isinstance(project, dict):
        if str(project.get("runner", "")).lower() in RUNNERS:
            merged["runner"] = str(project["runner"]).lower()
        for key in ("fix", "format", "report"):
            if isinstance(project.get(key), bool):
                merged[key] = project[key]
    return merged


def venv_ruff(root: Path) -> str | None:
    venv = root / ".venv"
    return shutil.which("ruff", path=os.pathsep.join([str(venv / "bin"), str(venv / "Scripts")]))


def ruff_command(root: Path, runner: str) -> list[str] | None:
    """The command prefix that runs the project's ruff, or None if there is none."""
    if runner in ("auto", "venv") and (found := venv_ruff(root)):
        return [found]
    if runner == "uv" and (uv := shutil.which("uv")):
        return [uv, "run", "--no-sync", "ruff"]  # --no-sync: never install anything
    poetry = shutil.which("poetry")
    if poetry and (runner == "poetry" or (runner == "auto" and (root / "poetry.lock").is_file())):
        return [poetry, "run", "ruff"]
    if runner in ("auto", "venv", "path") and (found := shutil.which("ruff")):
        return [found]
    return None


def run(cmd: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=str(root), capture_output=True, encoding="utf-8", errors="replace", timeout=TIMEOUT
    )


def first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "no output")


def warn_once(event: dict[str, Any], message: str) -> str | None:
    """The message the first time in a session, None afterwards."""
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not data:
        return message
    session = re.sub(r"[^A-Za-z0-9_-]", "_", str(event.get("session_id") or "unknown"))[:80]
    marker = Path(data) / f"ruff-missing-{session}"
    if marker.exists():
        return None
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        pass
    return message


def handle(event: dict[str, Any]) -> dict[str, Any] | None:
    """The JSON to print, or None for nothing to say."""
    raw = (event.get("tool_input") or {}).get("file_path")
    if not raw or Path(raw).suffix.lower() not in PY_SUFFIXES:
        return None
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()).resolve()
    path = Path(raw) if Path(raw).is_absolute() else root / raw
    try:
        rel = path.resolve().relative_to(root).as_posix()
    except ValueError:
        return None  # outside the project: not ours to reformat
    if not (root / rel).is_file():
        return None
    conf = settings(root)
    if not (conf["fix"] or conf["format"] or conf["report"]):
        return None
    ruff = ruff_command(root, conf["runner"])
    if ruff is None:
        note = warn_once(
            event,
            f"{PLUGIN}: ruff was not found (runner: {conf['runner']}), so Python files are not being "
            "fixed or formatted. Tell the user once; do not install anything without asking.",
        )
        return context(note) if note else None

    problems: list[str] = []
    errors: list[str] = []
    if conf["fix"] or conf["report"]:
        check = [*ruff, "check", "--force-exclude", "--output-format", "concise", "--quiet"]
        if conf["fix"]:
            check.append("--fix")
        result = run([*check, "--", rel], root)
        if result.returncode == 1:
            problems = [line for line in result.stdout.splitlines() if line.strip()]
        elif result.returncode != 0:
            errors.append(f"ruff check failed: {first_line(result.stderr or result.stdout)}")
    if conf["format"]:
        result = run([*ruff, "format", "--force-exclude", "--quiet", "--", rel], root)
        if result.returncode != 0 and not problems:  # a syntax error is already in problems
            errors.append(f"ruff format failed: {first_line(result.stderr or result.stdout)}")

    if problems and conf["report"]:
        shown = problems[:MAX_LINES]
        more = len(problems) - len(shown)
        reason = f"ruff found {len(problems)} problem(s) it could not fix in {rel}:\n" + "\n".join(shown)
        if more:
            reason += f"\n... and {more} more (run ruff check {rel})"
        out: dict[str, Any] = {"decision": "block", "reason": reason}
        if errors:
            out["hookSpecificOutput"] = context("\n".join(errors))["hookSpecificOutput"]
        return out
    if errors:
        return context("\n".join(errors))
    return None


def context(text: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}


def main() -> int:
    try:
        event = json.load(sys.stdin)
        out = handle(event if isinstance(event, dict) else {})
        if out:
            print(json.dumps(out))
    except Exception:
        if debug():
            raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
