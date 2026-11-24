"""The catalog, the manifests and hooks.json agree with each other and with the disk."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import ROOT, clean_env

MARKETPLACE = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
ENTRIES = MARKETPLACE["plugins"]
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_PREFIXES = ("claude-", "anthropic-", "anthropics-", "cc-plugin-")
HOOK_COMMAND = re.compile(r'^bash "\$\{CLAUDE_PLUGIN_ROOT\}/hooks/run\.sh" (\w+\.py)$')


def manifest(entry: dict) -> dict:
    path = ROOT / entry["source"] / ".claude-plugin" / "plugin.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_marketplace_name():
    assert MARKETPLACE["name"] == "working-bee"


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e["name"])
def test_entry_matches_its_plugin(entry):
    assert entry["source"].startswith("./plugins/")
    data = manifest(entry)
    assert data["name"] == entry["name"]
    assert KEBAB.match(data["name"])
    assert not data["name"].startswith(RESERVED_PREFIXES)
    assert re.match(r"^\d+\.\d+\.\d+$", data["version"])
    assert data["license"] == "MIT"
    assert (ROOT / entry["source"] / "README.md").is_file()


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e["name"])
def test_hook_commands_point_to_existing_scripts(entry):
    hooks_file = ROOT / entry["source"] / "hooks" / "hooks.json"
    if not hooks_file.exists():
        pytest.skip("plugin has no hooks")
    data = json.loads(hooks_file.read_text(encoding="utf-8"))
    assert set(data) >= {"hooks"}, "hooks.json must wrap the events in a top-level 'hooks' key"
    for groups in data["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                match = HOOK_COMMAND.match(hook["command"])
                assert match, f"unexpected hook command: {hook['command']}"
                assert (hooks_file.parent / match.group(1)).is_file()


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e["name"])
def test_skills_have_frontmatter(entry):
    for skill in (ROOT / entry["source"] / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        assert text.startswith("---\n"), skill
        front = text.split("---\n", 2)[1]
        assert re.search(rf"^name: {skill.parent.name}$", front, re.M), skill
        assert re.search(r"^description: .*Use when", front, re.M), f"{skill}: description needs 'Use when'"


def test_shell_scripts_use_lf():
    for script in ROOT.glob("plugins/*/hooks/*.sh"):
        assert b"\r\n" not in script.read_bytes(), f"{script} has CRLF line endings"


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not installed")
@pytest.mark.parametrize(
    ("script", "event", "code"),
    [
        ("guard_commands.py", {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}, 2),
        ("guard_commands.py", {"tool_name": "Bash", "tool_input": {"command": "ls"}}, 0),
        ("guard_files.py", {"tool_name": "Read", "tool_input": {"file_path": "/x/.env"}}, 2),
    ],
)
def test_launcher_finds_python_and_runs_the_hook(tmp_path: Path, script, event, code):
    run_sh = ROOT / "plugins" / "core" / "hooks" / "run.sh"
    proc = subprocess.run(
        # full path: on Windows a bare "bash" resolves to WSL (System32) before PATH
        [shutil.which("bash"), run_sh.as_posix(), script],
        input=json.dumps({"cwd": str(tmp_path), "hook_event_name": "PreToolUse", **event}),
        capture_output=True,
        text=True,
        env=clean_env(tmp_path),
        timeout=30,
    )
    assert proc.returncode == code, proc.stderr


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not installed")
def test_launcher_caches_python_and_survives_a_stale_cache(tmp_path: Path):
    run_sh = (ROOT / "plugins" / "core" / "hooks" / "run.sh").as_posix()
    data = tmp_path / "plugin-data"
    env = {**clean_env(tmp_path), "CLAUDE_PLUGIN_DATA": str(data)}
    event = json.dumps({"cwd": str(tmp_path), "tool_name": "Bash", "tool_input": {"command": "rm -rf ~"}})

    def run() -> int:
        bash = shutil.which("bash")
        return subprocess.run([bash, run_sh, "guard_commands.py"], input=event, text=True,
                              capture_output=True, env=env, timeout=30).returncode  # fmt: skip

    assert run() == 2
    assert (data / "python-cmd").read_text().strip()  # remembered
    assert run() == 2  # from the cache
    (data / "python-cmd").write_text("/nowhere/python\n\n")
    assert run() == 2  # stale cache: probes again
    assert "nowhere" not in (data / "python-cmd").read_text()


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e["name"])
def test_dependencies_resolve_in_this_marketplace(entry):
    names = {e["name"] for e in ENTRIES}
    for dep in manifest(entry).get("dependencies", []):
        name = dep if isinstance(dep, str) else dep["name"]
        assert "@" not in name or name.endswith("@working-bee"), name
        assert name.split("@")[0] in names, f"{entry['name']} depends on unknown plugin {name}"


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e["name"])
def test_skill_links_point_to_existing_files(entry):
    for skill in (ROOT / entry["source"] / "skills").glob("*/SKILL.md"):
        for target in re.findall(r"\]\((references/[^)]+)\)", skill.read_text(encoding="utf-8")):
            assert (skill.parent / target).is_file(), f"{skill}: broken link {target}"
