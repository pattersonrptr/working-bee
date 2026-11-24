"""privacy: sensitive terms and personal data ask before reaching files, commits, pushes or published text.

Every term and every piece of personal data here is made up, and built from split parts at runtime so the
fixtures are not literals (the repository's own privacy check reads this file too).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import PLUGINS, git, run_hook

TERM = "Acme" + "corp"
PERSONAL = "Globex" + "ian"
CPF_OK = "529.982" + ".247-25"  # valid check digits
CPF_BAD = "529.982" + ".247-26"
CNPJ_OK = "11.222.333" + "/0001-81"
EMAIL = "maria.souza" + "@" + "gmail.com"
PHONE = "(11) 98765" + "-4321"
CEP = "CEP " + "01310-100"
ADDRESS = "Rua das " + "Flores, 123"
BUILDING = "Condomínio " + "Jardim Azul"
HOST = "build01.acme" + ".corp"
IP = "10.20" + ".30.40"


def hook(project: Path, event: dict, **options: str):
    return run_hook("guard_terms.py", event, project, plugin="privacy", **options)


def write(project: Path, path: str, content: str, **options: str):
    tool_input = {"file_path": str(project / path), "content": content}
    return hook(
        project, {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": tool_input}, **options
    )


def edit(project: Path, old: str, new: str):
    tool_input = {"file_path": str(project / "a.md"), "old_string": old, "new_string": new}
    return hook(project, {"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": tool_input})


def shell(project: Path, command: str, tool: str = "Bash", **options: str):
    event = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": command}}
    return hook(project, event, **options)


def reason(result) -> str:
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.fixture(autouse=True)
def no_personal_list(tmp_path, monkeypatch):
    # the default personal list lives under the home folder: point it at an empty one
    home = tmp_path / "fake-home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


@pytest.fixture
def project(repo: Path) -> Path:
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


def allow(project: Path, settings: dict) -> None:
    (project / ".claude").mkdir(exist_ok=True)
    (project / ".claude" / "working-bee.json").write_text(json.dumps({"privacy": settings}))


# --- terms ------------------------------------------------------------------------


@pytest.mark.parametrize("text", [TERM, TERM.upper(), f"Worked at {TERM} Ltd.", "acmécorp"])
def test_write_with_a_term_asks(project, text):
    result = write(project, "notes.md", f"line one\n{text}\n")
    assert result.asked
    assert "a***p in notes.md:2" in reason(result)
    assert TERM.lower() not in result.stdout.lower()  # never echoed


def test_write_without_findings_passes(project):
    assert write(project, "notes.md", "the employer, a client\nabc\nuser@example.com\n").allowed


def test_term_in_the_path_asks_without_echoing_it(project):
    result = write(project, f"docs/{TERM}/plan.md", "nothing here")
    assert result.asked
    assert TERM.lower() not in result.stdout.lower()


def test_personal_terms_file_applies_too(project, personal):
    assert write(project, "a.md", f"hello {PERSONAL}", terms_file=personal).asked
    assert write(project, "a.md", f"hello {PERSONAL}").allowed


def test_default_personal_file_is_used_without_the_option(project, tmp_path):
    default = tmp_path / "fake-home" / ".config" / "working-bee" / "sensitive-terms.txt"
    default.parent.mkdir(parents=True)
    default.write_text(f"{PERSONAL}\n", encoding="utf-8")
    assert write(project, "a.md", f"hello {PERSONAL}").asked


def test_edit_that_adds_a_finding_asks_and_one_that_keeps_it_passes(project):
    assert edit(project, "client", TERM).asked
    assert edit(project, f"{TERM} sold widgets", f"{TERM} sold gadgets").allowed
    assert edit(project, f"mail {EMAIL} now", f"write to {EMAIL}").allowed


def test_multiedit_and_notebook_are_checked(project):
    multi = {"file_path": str(project / "a.md"), "edits": [{"old_string": "x", "new_string": TERM}]}
    assert hook(
        project, {"hook_event_name": "PreToolUse", "tool_name": "MultiEdit", "tool_input": multi}
    ).asked
    nb = {"notebook_path": str(project / "a.ipynb"), "new_source": f"print('{CPF_OK}')"}
    assert hook(
        project, {"hook_event_name": "PreToolUse", "tool_name": "NotebookEdit", "tool_input": nb}
    ).asked


def test_the_term_list_itself_can_be_edited(project):
    target = project / ".git" / "info" / "sensitive-terms"
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(target), "content": TERM},
    }
    assert hook(project, event).allowed


# --- detectors ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "label"),
    [
        (f"cpf: {CPF_OK}", "a CPF"),
        ("CPF " + "529982" + "24725", "a CPF"),
        (f"cnpj {CNPJ_OK}", "a CNPJ"),
        (f"contact {EMAIL}", "an e-mail address"),
        (f"ligar {PHONE}", "a phone number"),
        ("+55 11 " + "98765-4321", "a phone number"),
        ("whatsapp: 11 " + "98765 4321", "a phone number"),
        (CEP, "a CEP"),
        (f"moro na {ADDRESS}", "a street or building address"),
        ("Avenida " + "Paulista, nº 1000", "a street or building address"),
        (f"no {BUILDING}", "a street or building address"),
        (f"ssh {HOST}:22", "an internal host name"),
        (f"DB_HOST={IP}", "a private IP address"),
        ("gateway 192.168" + ".0.1", "a private IP address"),
    ],
)
def test_personal_data_asks(project, text, label):
    result = write(project, "notes.md", text)
    assert result.asked, text
    assert f"{label} in notes.md:1" in reason(result)


@pytest.mark.parametrize(
    "text",
    [
        f"cpf: {CPF_BAD}",  # wrong check digits
        "id " + "529982" + "24725",  # 11 digits with no CPF label
        "111.111" + ".111-11",  # all digits equal
        "user@example.com, dev@test, noreply@anthropic.com, git@github.com:owner/repo",
        "x@users.noreply.github.com",
        "version 10.2.3, port 8080, 2026-11-24, 1234-5678",
        "copy .claude/settings.local.json, CLAUDE.local.md and .env.local",
        "localhost:8000 and 127.0.0.1 and 8.8.8.8",
        "rua sem nome, a avenida principal",  # no proper name and number
        "npm install -g @anthropic-ai/claude-code",
        "def f(x): return x @ y",
    ],
)
def test_ordinary_text_passes(project, text):
    assert write(project, "notes.md", text).allowed, text


def test_project_can_allow_detectors_and_terms(project):
    allow(project, {"allow": ["email", "phone"], "allow_terms": [TERM]})
    assert write(project, "resume.md", f"{TERM}\n{EMAIL}\n{PHONE}\n").allowed
    assert write(project, "resume.md", f"cpf {CPF_OK}").asked  # not allowed


def test_detectors_option_off_keeps_terms(project):
    assert write(project, "a.md", EMAIL, detectors="false").allowed
    assert write(project, "a.md", TERM, detectors="false").asked


def test_detectors_work_without_any_term_list(repo):
    assert write(repo, "a.md", f"cpf {CPF_OK}").asked
    assert write(repo, "a.md", "hello").allowed


# --- commits and pushes ---------------------------------------------------------------


def stage(project: Path, name: str, content: str) -> None:
    (project / name).write_text(content, encoding="utf-8")
    git(project, "add", name)


def test_commit_with_staged_findings_asks(project):
    stage(project, "a.md", f"one\ntwo\n{TERM}\n{EMAIL}\n")
    result = shell(project, 'git commit -m "add notes"')
    assert result.asked
    assert "a.md:3" in reason(result) and "an e-mail address in a.md:4" in reason(result)


def test_clean_commit_passes_even_with_a_coauthor_line(project):
    stage(project, "a.md", "one\n")
    assert shell(project, 'git commit -m "x" -m "Co-Authored-By: Claude <noreply@anthropic.com>"').allowed
    assert shell(project, "git add a.md && git commit -m 'x'", tool="PowerShell").allowed


def test_commit_message_with_a_term_asks(project):
    stage(project, "a.md", "one\n")
    assert shell(project, f'git commit -m "port the {TERM} importer"').asked


def test_commit_all_checks_unstaged_tracked_changes(project):
    (project / "README.md").write_text(f"hello {TERM}\n", encoding="utf-8")
    assert shell(project, "git commit -m wip").allowed
    assert shell(project, "git commit -am wip").asked
    assert shell(project, "git commit --all -m wip").asked


def test_push_checks_commits_not_on_any_remote(project, tmp_path):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(project, "remote", "add", "origin", str(remote))
    git(project, "push", "-q", "origin", "feat/x")
    assert shell(project, "git push").allowed

    stage(project, "a.md", f"{CEP}\n")
    git(project, "commit", "-q", "-m", "notes")
    result = shell(project, "git push origin feat/x")
    assert result.asked and "a CEP in a.md:1" in reason(result)


def test_push_checks_commit_messages(project):
    stage(project, "a.md", "clean\n")
    git(project, "commit", "-q", "-m", f"for {TERM}")
    assert shell(project, "git push -u origin feat/x").asked


@pytest.mark.parametrize(
    "command",
    [
        f'gh pr create --title "x" --body "built for {TERM}"',
        f"curl -d 'email={EMAIL}' https://example.com",
        f"cd x; gh issue comment 1 --body 'server {HOST}'",
    ],
)
def test_publishing_commands_with_findings_ask(project, command):
    assert shell(project, command).asked


@pytest.mark.parametrize("command", [f"grep -rn {TERM} src", f"echo {EMAIL}", "gh pr list", "ls"])
def test_other_commands_pass(project, command):
    assert shell(project, command).allowed


# --- session start and odd input -------------------------------------------------------


def test_session_start_counts_terms_and_lists_detectors(project, personal):
    allow(project, {"allow": ["email"]})
    result = hook(project, {"hook_event_name": "SessionStart", "source": "startup"}, terms_file=personal)
    assert result.code == 0  # SessionStart stdout is plain text context, not JSON
    assert "2 sensitive term(s) loaded" in result.stdout
    assert "detectors: phone, cpf" in result.stdout and "allowed in this project: email" in result.stdout
    assert TERM.lower() not in result.stdout.lower()


def test_session_start_says_when_there_are_no_terms(repo):
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


# --- terms CLI ---------------------------------------------------------------------------


def cli(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    script = PLUGINS / "privacy" / "hooks" / "terms_cli.py"
    return subprocess.run(
        [sys.executable, "-I", str(script), *args],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_cli_adds_to_the_personal_list_without_printing_terms(project, tmp_path):
    out = cli(project, "add", PERSONAL, "x")
    assert out.returncode == 0
    assert PERSONAL.lower() not in out.stdout.lower() and "added sensitive term g***n" in out.stdout
    personal = tmp_path / "fake-home" / ".config" / "working-bee" / "sensitive-terms.txt"
    assert PERSONAL in personal.read_text(encoding="utf-8")
    assert "already listed" in cli(project, "add", PERSONAL.upper()).stdout
    assert "personal: 1 term(s)" in cli(project, "count").stdout


def test_cli_adds_to_the_repository_list(project):
    cli(project, "add", "--repo", PERSONAL)
    assert "this repository: 2 term(s)" in cli(project, "count").stdout
    assert write(project, "a.md", PERSONAL).asked


def test_cli_check_says_covered_or_not(project):
    out = cli(project, "check", f"the {TERM} team", "nothing").stdout.splitlines()
    assert out[0].startswith("covered") and out[1].startswith("not covered")
    assert TERM.lower() not in "\n".join(out).lower()
