"""Hooks are tested the way Claude Code runs them: a subprocess fed JSON on stdin."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE_HOOKS = ROOT / "plugins" / "core" / "hooks"


@dataclass
class Result:
    code: int
    stdout: str
    stderr: str

    @property
    def denied(self) -> bool:
        return self.code == 2

    @property
    def asked(self) -> bool:
        if self.code != 0 or not self.stdout.strip():
            return False
        out = json.loads(self.stdout)
        return out["hookSpecificOutput"]["permissionDecision"] == "ask"

    @property
    def allowed(self) -> bool:
        return self.code == 0 and not self.asked


def clean_env(project: Path, **options: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env["WORKING_BEE_DEBUG"] = "1"  # a crash must fail the test, not look like "allowed"
    for key, value in options.items():
        env[f"CLAUDE_PLUGIN_OPTION_{key.upper()}"] = value
    return env


def run_hook(script: str, event: dict, project: Path, **options: str) -> Result:
    event = {"session_id": "test", "cwd": str(project), **event}
    proc = subprocess.run(
        [sys.executable, "-I", str(CORE_HOOKS / script)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=clean_env(project, **options),
        timeout=30,
    )
    return Result(proc.returncode, proc.stdout, proc.stderr)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repository on ``main`` with one commit."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test")
    git(path, "config", "commit.gpgsign", "false")
    (path / "README.md").write_text("hello\n")
    git(path, "add", "README.md")
    git(path, "commit", "-q", "-m", "init")
    return path


@pytest.fixture
def feature(repo: Path) -> Path:
    """The same repository, checked out on a feature branch."""
    git(repo, "switch", "-q", "-c", "feat/x")
    return repo


def write_project_config(repo: Path, core: dict) -> None:
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude" / "working-bee.json").write_text(json.dumps({"core": core}))
