"""guard_files: secrets, frozen paths and the guardrails' own configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import git, run_hook, write_project_config


def file_tool(tool: str, path: Path | str, project: Path, **options: str):
    key = {"NotebookEdit": "notebook_path", "Grep": "path"}.get(tool, "file_path")
    event = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {key: str(path)}}
    return run_hook("guard_files.py", event, project, **options)


# --- secrets ----------------------------------------------------------------


@pytest.mark.parametrize("tool", ["Read", "Edit", "Write", "MultiEdit", "Grep"])
def test_env_file_is_denied_for_every_tool(feature, tool):
    result = file_tool(tool, feature / ".env", feature)
    assert result.denied
    assert ".env holds secrets" in result.stderr


@pytest.mark.parametrize(
    "name",
    [".env.local", ".env.production", "server.pem", "tls.key", "id_rsa", "id_ed25519", ".netrc", "cert.pfx"],
)
def test_secret_files_are_denied(feature, name):
    assert file_tool("Read", feature / "config" / name, feature).denied


@pytest.mark.parametrize(
    "name", [".env.example", ".env.sample", ".env.template", "id_rsa.pub", "keys.py", "environment.md"]
)
def test_lookalikes_pass(feature, name):
    assert file_tool("Read", feature / name, feature).allowed
    assert file_tool("Write", feature / name, feature).allowed


def test_secret_outside_the_project_is_denied_too(feature, tmp_path):
    assert file_tool("Read", tmp_path / "home" / ".ssh" / "id_rsa", feature).denied


def test_windows_style_path_is_understood(feature):
    assert file_tool("Read", "C:\\Users\\me\\project\\.env", feature).denied


# --- guardrail configuration asks -------------------------------------------


@pytest.mark.parametrize(
    "rel",
    [
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/hooks/x.py",
        ".claude/working-bee.json",
        ".githooks/pre-commit",
    ],
)
def test_guard_config_edits_ask(feature, rel):
    result = file_tool("Edit", feature / rel, feature)
    assert result.asked
    assert "guardrails" in result.stdout


def test_reading_guard_config_passes(feature):
    assert file_tool("Read", feature / ".claude" / "settings.json", feature).allowed


def test_project_ask_paths_add_to_defaults(feature):
    write_project_config(feature, {"ask_paths": ["infra/**"]})
    assert file_tool("Write", feature / "infra" / "prod" / "main.tf", feature).asked
    assert file_tool("Write", feature / ".claude" / "settings.json", feature).asked
    assert file_tool("Write", feature / "src" / "app.py", feature).allowed


# --- frozen paths -------------------------------------------------------------


@pytest.fixture
def migrations(feature: Path) -> Path:
    versions = feature / "backend" / "alembic" / "versions"
    versions.mkdir(parents=True)
    (versions / "0001_init.py").write_text("# applied\n")
    git(feature, "switch", "-q", "main")
    git(feature, "add", ".")
    git(feature, "commit", "-q", "-m", "migration")
    git(feature, "switch", "-q", "feat/x")
    git(feature, "merge", "-q", "main")
    write_project_config(feature, {"frozen_paths": ["backend/alembic/versions/*.py"]})
    return versions


def test_frozen_file_on_main_is_denied(feature, migrations):
    result = file_tool("Edit", migrations / "0001_init.py", feature)
    assert result.denied
    assert "already on main" in result.stderr


def test_new_file_under_frozen_pattern_passes(feature, migrations):
    assert file_tool("Write", migrations / "0002_new.py", feature).allowed


def test_reading_frozen_file_passes(feature, migrations):
    assert file_tool("Read", migrations / "0001_init.py", feature).allowed


def test_no_frozen_paths_by_default(feature, migrations):
    (feature / ".claude" / "working-bee.json").unlink()
    assert file_tool("Edit", migrations / "0001_init.py", feature).allowed


# --- noise --------------------------------------------------------------------


def test_regular_files_pass(feature):
    assert file_tool("Edit", feature / "src" / "app.py", feature).allowed
    assert file_tool("NotebookEdit", feature / "nb.ipynb", feature).allowed


def test_missing_path_passes(feature):
    event = {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "x"}}
    assert run_hook("guard_files.py", event, feature).allowed
