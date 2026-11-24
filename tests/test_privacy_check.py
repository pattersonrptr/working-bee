"""tools/privacy_check.py: secrets and private terms never reach a commit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ROOT, git

CHECK = ROOT / "tools" / "privacy_check.py"


def check(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(CHECK), *args], cwd=repo, capture_output=True, text=True)


def stage(repo: Path, name: str, content: str) -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    git(repo, "add", "-f", name)


def test_clean_change_passes(repo):
    stage(repo, "docs/notes.md", "nothing to see\n")
    assert check(repo).returncode == 0


@pytest.mark.parametrize(
    "content",
    [
        "token = 'ghp_" + "a" * 36 + "'",
        "key: sk-ant-" + "b" * 30,
        "AKIA" + "C" * 16,
        "-----BEGIN OPENSSH " + "PRIVATE KEY-----",
    ],
)
def test_credentials_are_caught(repo, content):
    stage(repo, "config.py", content + "\n")
    result = check(repo)
    assert result.returncode == 1
    assert "looks like a credential" in result.stderr


@pytest.mark.parametrize("name", [".env", "deploy/.env.production", "certs/server.pem", "id_ed25519"])
def test_secret_files_are_caught(repo, name):
    stage(repo, name, "x\n")
    assert "secret file" in check(repo).stderr


def test_env_template_passes(repo):
    stage(repo, ".env.example", "API_KEY=\n")
    assert check(repo).returncode == 0


def test_sensitive_terms_are_caught_without_printing_them(repo):
    (repo / ".git" / "info").mkdir(exist_ok=True)
    (repo / ".git" / "info" / "sensitive-terms").write_text("# comment\nAcme Construção\n", encoding="utf-8")
    stage(repo, "README.md", "Built at ACME CONSTRUCAO in 2026\n")
    result = check(repo)
    assert result.returncode == 1
    assert "sensitive term" in result.stderr
    assert "acme" not in result.stderr.lower()


def test_all_mode_checks_tracked_files(repo):
    (repo / "README.md").write_text("ghp_" + "z" * 36 + "\n")
    git(repo, "commit", "-qam", "oops", "--no-verify")
    assert check(repo, "--all").returncode == 1
