"""privacy guard_terms: sensitive terms never reach files, commits, pushes or published text.

The terms here are made up; real lists live outside the repository.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import git, run_hook

TERM = "Acme" + "corp"  # split so the fixture itself is not one literal
PERSONAL = "Globex" + "ian"


def hook(project: Path, event: dict, **options: str):
    return run_hook("guard_terms.py", event, project, plugin="privacy", **options)


def write(project: Path, path: str, content: str, **options: str):
    tool_input = {"file_path": str(project / path), "content": content}
    return hook(
        project, {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": tool_input}, **options
    )


def shell(project: Path, command: str, tool: str = "Bash", **options: str):
    event = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": command}}
    return hook(project, event, **options)


@pytest.fixture
def project(repo: Path) -> Path:
    """The conftest repository on a feature branch, with a project term list."""
    git(repo, "switch", "-q", "-c", "feat/x")
    (repo / ".git" / "info").mkdir(exist_ok=True)
    (repo / ".git" / "info" / "sensitive-terms").write_text(f"# employer\n{TERM}\n\nab\n", encoding="utf-8")
    return repo


@pytest.fixture
def personal(tmp_path: Path) -> str:
    path = tmp_path / "home" / "terms.txt"
    path.parent.mkdir()
    path.write_text(f"{PERSONAL}\n", encoding="utf-8")
    return str(path)


# --- file tools -------------------------------------------------------------


@pytest.mark.parametrize("text", [TERM, TERM.upper(), f"Worked at {TERM} Ltd.", "acmécorp"])
def test_write_with_a_term_is_blocked(project, text):
    result = write(project, "notes.md", f"line one\n{text}\n")
    assert result.denied
    assert "a***p in notes.md:2" in result.stderr
    assert TERM.lower() not in result.stderr.lower()  # the term itself is never echoed


def test_write_without_terms_passes(project):
    assert write(
        project, "notes.md", "the employer, a client\nabc\n"
    ).allowed  # "ab" is too short to be a term


def test_term_in_the_path_is_blocked_without_echoing_it(project):
    result = write(project, f"docs/{TERM}/plan.md", "nothing here")
    assert result.denied
    assert TERM.lower() not in result.stderr.lower()


def test_personal_terms_file_applies_too(project, personal):
    assert write(project, "a.md", f"hello {PERSONAL}", terms_file=personal).denied
    assert write(project, "a.md", f"hello {PERSONAL}").allowed  # without the option it is unknown


def test_edit_that_adds_a_term_is_blocked(project):
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": str(project / "a.md"), "old_string": "client", "new_string": TERM},
    }
    assert hook(project, event).denied


def test_edit_that_keeps_an_existing_term_passes(project):
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": str(project / "old.md"),
            "old_string": f"{TERM} sold widgets",
            "new_string": f"{TERM} sold gadgets",
        },
    }
    assert hook(project, event).allowed


def test_multiedit_and_notebook_are_checked(project):
    multi = {"file_path": str(project / "a.md"), "edits": [{"old_string": "x", "new_string": TERM}]}
    assert hook(
        project, {"hook_event_name": "PreToolUse", "tool_name": "MultiEdit", "tool_input": multi}
    ).denied
    nb = {"notebook_path": str(project / "a.ipynb"), "new_source": f"print('{TERM}')"}
    assert hook(
        project, {"hook_event_name": "PreToolUse", "tool_name": "NotebookEdit", "tool_input": nb}
    ).denied


def test_the_term_list_itself_can_be_edited(project):
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(project / ".git" / "info" / "sensitive-terms"), "content": TERM},
    }
    assert hook(project, event).allowed


def test_without_terms_nothing_is_checked(repo):
    assert write(repo, "a.md", TERM).allowed


# --- commits and pushes -------------------------------------------------------


def stage(project: Path, name: str, content: str) -> None:
    (project / name).write_text(content, encoding="utf-8")
    git(project, "add", name)


def test_commit_with_a_staged_term_is_blocked(project):
    stage(project, "a.md", f"one\ntwo\n{TERM}\n")
    result = shell(project, 'git commit -m "add notes"')
    assert result.denied
    assert "a.md:3" in result.stderr


def test_clean_commit_passes(project):
    stage(project, "a.md", "one\n")
    assert shell(project, 'git commit -m "add notes"').allowed
    assert shell(project, "git add a.md && git commit -m 'x'", tool="PowerShell").allowed


def test_commit_message_with_a_term_is_blocked(project):
    stage(project, "a.md", "one\n")
    assert shell(project, f'git commit -m "port the {TERM} importer"').denied


def test_commit_all_checks_unstaged_tracked_changes(project):
    (project / "README.md").write_text(f"hello {TERM}\n", encoding="utf-8")  # tracked, not staged
    assert shell(project, "git commit -m wip").allowed
    assert shell(project, "git commit -am wip").denied
    assert shell(project, "git commit --all -m wip").denied


def test_push_checks_commits_not_on_any_remote(project, tmp_path):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(project, "remote", "add", "origin", str(remote))
    git(project, "push", "-q", "origin", "feat/x")
    assert shell(project, "git push").allowed  # nothing new

    stage(project, "a.md", f"{TERM}\n")
    git(project, "commit", "-q", "-m", "notes")
    result = shell(project, "git push origin feat/x")
    assert result.denied and "a.md:1" in result.stderr


def test_push_checks_commit_messages(project):
    stage(project, "a.md", "clean\n")
    git(project, "commit", "-q", "-m", f"for {TERM}")
    assert shell(project, "git push -u origin feat/x").denied


@pytest.mark.parametrize(
    "command",
    [
        f'gh pr create --title "x" --body "built for {TERM}"',
        f"curl -d 'name={TERM}' https://example.com",
        f"cd x; gh issue comment 1 --body '{TERM}'",
    ],
)
def test_publishing_commands_with_a_term_are_blocked(project, command):
    assert shell(project, command).denied


@pytest.mark.parametrize("command", [f"grep -rn {TERM} src", f"echo {TERM}", "gh pr list", "ls"])
def test_other_commands_pass(project, command):
    # searching for a term locally is fine: only what gets written or published is checked
    assert shell(project, command).allowed


# --- session start and odd input ------------------------------------------------


def test_session_start_counts_terms_without_naming_them(project, personal):
    result = hook(project, {"hook_event_name": "SessionStart", "source": "startup"}, terms_file=personal)
    assert result.code == 0  # SessionStart stdout is plain text context, not JSON
    assert "2 sensitive term(s) loaded" in result.stdout
    assert TERM.lower() not in result.stdout.lower()


def test_session_start_warns_when_there_are_no_terms(repo):
    assert "no sensitive terms configured" in hook(repo, {"hook_event_name": "SessionStart"}).stdout


@pytest.mark.parametrize(
    "event",
    [
        {},
        {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "x"}},
        {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {}},
        {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {}},
    ],
)
def test_unexpected_input_passes(project, event):
    assert hook(project, event).allowed
