"""python-backend ruff_after_edit: fix and format the edited Python file, report what is left."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from conftest import run_hook

RUFF = shutil.which("ruff")
pytestmark = pytest.mark.skipif(RUFF is None, reason="ruff not installed")

MESSY = "import os\nx=1\n"  # F401 (fixable) and formatting
CLEAN = "x = 1\n"
BROKEN = "print(undefined_name)\n"  # F821: ruff cannot fix it


def edit(project: Path, path: Path | str, tool: str = "Edit", env: dict | None = None, **options: str):
    event = {
        "hook_event_name": "PostToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": str(path)},
        "tool_response": {},
    }
    return run_hook("ruff_after_edit.py", event, project, plugin="python-backend", env=env, **options)


def output(result) -> dict:
    assert result.code == 0, result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else {}


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "project"
    path.mkdir()
    (path / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0"\n')
    return path


def config(project: Path, settings: dict) -> None:
    (project / ".claude").mkdir(exist_ok=True)
    (project / ".claude" / "working-bee.json").write_text(json.dumps({"python-backend": settings}))


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
def test_edited_file_is_fixed_and_formatted(project, tool):
    target = project / "app.py"
    target.write_text(MESSY)
    assert output(edit(project, target, tool)) == {}
    assert target.read_text() == CLEAN


def test_problems_ruff_cannot_fix_go_back_to_claude(project):
    target = project / "pkg" / "mod.py"
    target.parent.mkdir()
    target.write_text("import os\n" + BROKEN)
    out = output(edit(project, target))
    assert out["decision"] == "block"
    assert "F821" in out["reason"] and "pkg/mod.py" in out["reason"]
    assert "import os" not in target.read_text()  # the fixable part was still fixed


def test_relative_path_is_resolved_from_the_project(project):
    (project / "app.py").write_text(MESSY)
    output(edit(project, "app.py"))
    assert (project / "app.py").read_text() == CLEAN


@pytest.mark.parametrize("name", ["README.md", "data.json", "script.sh"])
def test_non_python_files_are_left_alone(project, name):
    target = project / name
    target.write_text(MESSY)
    assert output(edit(project, target)) == {}
    assert target.read_text() == MESSY


def test_file_outside_the_project_is_left_alone(project, tmp_path):
    outside = tmp_path / "elsewhere.py"
    outside.write_text(MESSY)
    assert output(edit(project, outside)) == {}
    assert outside.read_text() == MESSY


def test_ruff_exclude_is_respected(project):
    (project / "pyproject.toml").write_text('[tool.ruff]\nextend-exclude = ["legacy"]\n')
    target = project / "legacy" / "old.py"
    target.parent.mkdir()
    target.write_text(MESSY + BROKEN)
    assert output(edit(project, target)) == {}
    assert target.read_text() == MESSY + BROKEN


def test_project_config_turns_off_format_and_report(project):
    config(project, {"format": False, "report": False})
    target = project / "app.py"
    target.write_text("import os\nx=1\n" + BROKEN)
    assert output(edit(project, target)) == {}
    assert target.read_text() == "x=1\n" + BROKEN  # fixed, not formatted, nothing reported


def test_fix_off_still_reports(project):
    config(project, {"fix": False, "format": False})
    target = project / "app.py"
    target.write_text(MESSY)
    out = output(edit(project, target))
    assert "F401" in out["reason"]
    assert target.read_text() == MESSY


def test_syntax_error_is_reported_once(project):
    target = project / "app.py"
    target.write_text("def broken(:\n")
    out = output(edit(project, target))
    assert out["decision"] == "block"
    assert "hookSpecificOutput" not in out  # no second "format failed" message


def test_project_venv_ruff_is_used_first(project, tmp_path):
    for folder in ("bin", "Scripts"):  # POSIX and Windows layouts
        (project / ".venv" / folder).mkdir(parents=True)
        shutil.copy2(RUFF, project / ".venv" / folder / Path(RUFF).name)
    empty = tmp_path / "empty-path"
    empty.mkdir()
    target = project / "app.py"
    target.write_text(MESSY)
    assert output(edit(project, target, env={"PATH": str(empty)})) == {}
    assert target.read_text() == CLEAN


def test_missing_ruff_is_reported_once_per_session(project, tmp_path):
    empty = tmp_path / "empty-path"
    empty.mkdir()
    env = {"PATH": str(empty), "CLAUDE_PLUGIN_DATA": str(tmp_path / "data")}
    target = project / "app.py"
    target.write_text(MESSY)
    first = output(edit(project, target, env=env))
    assert "ruff was not found" in first["hookSpecificOutput"]["additionalContext"]
    assert output(edit(project, target, env=env)) == {}
    assert target.read_text() == MESSY


@pytest.mark.parametrize("runner", ["uv", "poetry"])
def test_forced_runner_that_is_missing_does_not_fall_back(project, tmp_path, runner):
    empty = tmp_path / "empty-path"
    empty.mkdir()
    target = project / "app.py"
    target.write_text(MESSY)
    out = output(edit(project, target, env={"PATH": str(empty)}, runner=runner))
    assert f"runner: {runner}" in out["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize("event", [{}, {"tool_input": {}}, {"tool_input": {"file_path": None}}])
def test_unexpected_input_passes_quietly(project, event):
    result = run_hook("ruff_after_edit.py", event, project, plugin="python-backend")
    assert output(result) == {}
