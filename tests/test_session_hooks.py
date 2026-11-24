"""session_brief and pre_compact: informative, and never blocking."""

from __future__ import annotations

from conftest import run_hook, write_project_config


def brief(project, **options):
    options.setdefault("brief_open_prs", "false")  # no network in tests
    return run_hook(
        "session_brief.py", {"hook_event_name": "SessionStart", "source": "startup"}, project, **options
    )


def test_brief_shows_branch_and_changes(feature):
    (feature / "README.md").write_text("changed\n")
    result = brief(feature)
    assert result.code == 0
    assert "Branch: feat/x; 1 changed tracked file(s)" in result.stdout


def test_brief_warns_on_protected_branch(repo):
    assert "(protected: work on a feature branch)" in brief(repo).stdout


def test_brief_points_to_read_first_files_that_exist(feature):
    (feature / "docs").mkdir()
    (feature / "docs" / "plan.md").write_text("# plan\n")
    write_project_config(feature, {"brief": {"read_first": ["docs/plan.md", "docs/missing.md"]}})
    out = brief(feature).stdout
    assert "Read before planning: docs/plan.md" in out
    assert "missing" not in out


def test_brief_warns_about_invalid_project_file(feature):
    (feature / ".claude").mkdir()
    (feature / ".claude" / "working-bee.json").write_text("[1, 2]")
    assert "WARNING: .claude/working-bee.json" in brief(feature).stdout


def test_brief_outside_git_is_silent(tmp_path):
    result = brief(tmp_path)
    assert result.code == 0
    assert result.stdout == ""


def test_pre_compact_lists_git_facts(feature):
    (feature / "new.txt").write_text("x\n")
    result = run_hook("pre_compact.py", {"hook_event_name": "PreCompact", "trigger": "auto"}, feature)
    assert result.code == 0
    assert "Current branch: feat/x" in result.stdout
    assert "new.txt" in result.stdout
    assert "init" in result.stdout  # the last commit


def test_pre_compact_outside_git_is_silent(tmp_path):
    result = run_hook("pre_compact.py", {"hook_event_name": "PreCompact", "trigger": "manual"}, tmp_path)
    assert (result.code, result.stdout) == (0, "")
