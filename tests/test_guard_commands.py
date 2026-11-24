"""guard_commands: every rule has a case that must be stopped and one that must pass."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import run_hook, write_project_config


def bash(command: str, project: Path, tool: str = "Bash", **options: str):
    event = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": command}}
    return run_hook("guard_commands.py", event, project, **options)


# --- commit and push on protected branches --------------------------------


def test_commit_on_main_is_denied(repo):
    result = bash('git commit -m "x"', repo)
    assert result.denied
    assert "protected branch main" in result.stderr


def test_commit_on_feature_branch_passes(feature):
    assert bash('git commit -m "x"', feature).allowed


def test_commit_after_switching_branch_in_same_command_passes(repo):
    assert bash('git switch -c feat/y && git commit -m "x"', repo).allowed


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git push origin HEAD:main",
        "git push origin feat/x:refs/heads/main",
        "git push origin :main",
        "git push origin --delete main",
    ],
)
def test_push_to_main_is_denied(feature, command):
    assert bash(command, feature).denied


def test_bare_push_from_main_is_denied(repo):
    assert bash("git push", repo).denied


def test_push_feature_branch_passes(feature):
    assert bash("git push -u origin feat/x", feature).allowed
    assert bash("git push", feature).allowed


def test_force_push_to_main_is_denied(feature):
    result = bash("git push --force origin main", feature)
    assert result.denied
    assert "force push" in result.stderr


def test_plus_refspec_to_main_is_denied(feature):
    assert bash("git push origin +feat/x:main", feature).denied


def test_force_push_to_feature_branch_asks(feature):
    assert bash("git push --force-with-lease origin feat/x", feature).asked


def test_push_mirror_is_denied(feature):
    assert bash("git push --mirror origin", feature).denied


def test_git_dash_c_checks_that_repository(repo, tmp_path):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    event_cwd_project = outside  # the hook runs from another folder
    assert bash(f'git -C "{repo}" commit -m x', event_cwd_project).denied


# --- protected branches come from options and the project file -------------


def test_option_changes_protected_branches(feature):
    assert bash('git commit -m "x"', feature, protected_branches="feat/x").denied
    assert bash("git push origin main", feature, protected_branches="develop").allowed


def test_project_file_overrides_option(feature):
    write_project_config(feature, {"protected_branches": ["develop"]})
    assert bash("git push origin main", feature, protected_branches="main").allowed
    assert bash("git push origin develop", feature).denied


def test_invalid_project_file_falls_back_to_defaults(repo):
    (repo / ".claude").mkdir()
    (repo / ".claude" / "working-bee.json").write_text("{not json")
    assert bash('git commit -m "x"', repo).denied


# --- skipping hooks and protections ---------------------------------------


@pytest.mark.parametrize(
    "command", ['git commit --no-verify -m "x"', 'git commit -n -m "x"', "git push --no-verify"]
)
def test_no_verify_is_denied(feature, command):
    result = bash(command, feature)
    assert result.denied
    assert "no-verify" in result.stderr


def test_push_dry_run_short_flag_passes(feature):
    assert bash("git push -n origin feat/x", feature).allowed  # -n is --dry-run for push


def test_gh_admin_merge_is_denied(feature):
    assert bash("gh pr merge 12 --squash --admin", feature).denied
    assert bash("gh pr merge 12 --squash", feature).allowed


# --- destructive but legitimate: ask ---------------------------------------


def test_reset_hard_asks(feature):
    assert bash("git reset --hard HEAD~1", feature).asked
    assert bash("git reset --soft HEAD~1", feature).allowed


def test_clean_force_asks(feature):
    assert bash("git clean -fd", feature).asked
    assert bash("git clean -n", feature).allowed


# --- recursive deletes ------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf /",
        "rm -rf ~",
        "rm -rf ~/",
        "rm -fr $HOME",
        "rm -rf .",
        "rm -rf *",
        "rm -r ..",
        "sudo rm -rf /*",
    ],
)
def test_catastrophic_rm_is_denied(feature, command):
    assert bash(command, feature).denied


@pytest.mark.parametrize(
    "command",
    ["Remove-Item -Recurse -Force C:\\", "Remove-Item -Recurse $env:USERPROFILE", "rd /s /q C:\\"],
)
def test_catastrophic_powershell_delete_is_denied(feature, command):
    assert bash(command, feature, tool="PowerShell").denied


@pytest.mark.parametrize("command", ["rm -rf build", "rm -rf ./node_modules", "rm file.txt", "rm -f *.pyc"])
def test_scoped_rm_passes(feature, command):
    assert bash(command, feature).allowed


# --- secrets ----------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    ["cat .env", "head -5 backend/.env.local", "grep KEY .env", "type .env", "Get-Content ~/.ssh/id_ed25519"],
)
def test_printing_secrets_is_denied(feature, command):
    assert bash(command, feature).denied


@pytest.mark.parametrize(
    "command", ["cat .env.example", "cat README.md", "grep -r env src/", "docker compose --env-file .env up"]
)
def test_non_secret_reads_pass(feature, command):
    assert bash(command, feature).allowed


@pytest.mark.parametrize(
    "command",
    [
        "grep -c KEY .env",  # -c takes no value: .env is still the file
        "grep -A 3 KEY config/.env",
        "grep -e KEY -e TOKEN .env",
        "rg -i --glob '*.py' KEY .env.local",
        "git ls-files | grep x && grep KEY .env",
        "findstr /s /i KEY .env",
        "Select-String -Pattern KEY -Path .env",
        "Select-String KEY .env",
    ],
)
def test_search_of_a_secret_file_is_denied(feature, command):
    assert bash(command, feature).denied


@pytest.mark.parametrize(
    "command",
    [
        "git ls-files | grep -Ei '\\.env|\\.pem'",  # a pattern that mentions .env is not the file
        "grep -rn '\\.env' src/",
        "rg -n '.env' docs",
        "grep -E 'id_rsa|\\.key' list.txt",
        "findstr /c:.env notes.txt",
        "Select-String -Pattern '.env' -Path README.md",
    ],
)
def test_search_pattern_naming_a_secret_passes(feature, command):
    assert bash(command, feature).allowed


def test_staging_secret_is_denied(feature):
    assert bash("git add .env", feature).denied
    assert bash("git add -f config/server.pem", feature).denied
    assert bash("git add .env.example src/", feature).allowed


# --- chains and noise -------------------------------------------------------


def test_deny_wins_inside_a_chain(feature):
    assert bash("git status && git push origin main", feature).denied


def test_commit_message_lines_are_not_commands(feature):
    command = "git commit -m \"$(cat <<'EOF'\nfix: never run rm -rf / again\nEOF\n)\""
    assert bash(command, feature).allowed


def test_empty_or_odd_input_passes(feature):
    assert bash("", feature).allowed
    assert bash('echo "unbalanced', feature).allowed


def test_broken_input_fails_open(feature):
    import subprocess
    import sys

    from conftest import CORE_HOOKS, clean_env

    proc = subprocess.run(
        [sys.executable, "-I", str(CORE_HOOKS / "guard_commands.py")],
        input="not json",
        capture_output=True,
        text=True,
        env={**clean_env(feature), "WORKING_BEE_DEBUG": "0"},
    )
    assert proc.returncode == 0
