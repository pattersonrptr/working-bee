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


AGENT_MODELS = {"sonnet", "opus", "haiku", "fable", "inherit"}
# Claude Code ignores these in plugin agents (security): a plugin that sets them only looks protected.
IGNORED_IN_PLUGIN_AGENTS = ("hooks", "mcpServers", "permissionMode", "initialPrompt")
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def agent_files() -> list[Path]:
    return sorted(path for entry in ENTRIES for path in (ROOT / entry["source"] / "agents").glob("*.md"))


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    fields = {}
    for line in text.split("---\n", 2)[1].splitlines():
        key, sep, value = line.partition(":")
        if sep and not key.startswith(" "):
            fields[key.strip()] = value.strip()
    return fields


@pytest.mark.parametrize("path", agent_files(), ids=lambda p: p.stem)
def test_agents_have_valid_frontmatter(path: Path):
    fields = frontmatter(path)
    assert fields.get("name") == path.stem
    assert "Use when" in fields.get("description", ""), f"{path.name}: description needs 'Use when'"
    assert fields.get("model") in AGENT_MODELS
    for key in IGNORED_IN_PLUGIN_AGENTS:
        assert key not in fields, f"{path.name}: '{key}' is ignored in plugin agents"


@pytest.mark.parametrize(
    "path", [p for p in agent_files() if p.stem.endswith("-reviewer")], ids=lambda p: p.stem
)
def test_reviewers_cannot_edit(path: Path):
    tools = {tool.strip() for tool in frontmatter(path)["tools"].split(",")}
    assert tools and not tools & WRITE_TOOLS, f"{path.name}: a reviewer must not have {tools & WRITE_TOOLS}"


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e["name"])
def test_skills_name_agents_that_exist(entry):
    plugin = ROOT / entry["source"]
    for skill in plugin.glob("skills/*/SKILL.md"):
        for agent in re.findall(rf"`{entry['name']}:([a-z0-9-]+)`", skill.read_text(encoding="utf-8")):
            assert (plugin / "agents" / f"{agent}.md").is_file(), f"{skill} names a missing agent: {agent}"


def test_every_launcher_is_a_copy_of_cores():
    # a plugin cannot reach another plugin's files once installed, so each one ships its own run.sh
    core = (ROOT / "plugins" / "core" / "hooks" / "run.sh").read_bytes()
    for launcher in ROOT.glob("plugins/*/hooks/run.sh"):
        assert launcher.read_bytes() == core, f"{launcher} differs from core's run.sh: copy it again"


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


BOOTSTRAP = ROOT / "plugins" / "bootstrap" / "skills" / "bootstrap"


@pytest.mark.parametrize(
    ("asset", "source"),
    [
        ("assets/tools/privacy_check.py", "tools/privacy_check.py"),
        ("assets/githooks/pre-commit", ".githooks/pre-commit"),
    ],
)
def test_bootstrap_ships_the_same_privacy_check_this_repo_runs(asset, source):
    assert (BOOTSTRAP / asset).read_bytes() == (ROOT / source).read_bytes(), f"copy {source} to {asset} again"


def test_bootstrap_settings_examples_are_valid_and_point_here():
    text = (BOOTSTRAP / "references" / "settings.md").read_text(encoding="utf-8")
    blocks = [json.loads(b) for b in re.findall(r"```json\n(.*?)```", text, re.S)]
    settings = blocks[0]
    repo = settings["extraKnownMarketplaces"][MARKETPLACE["name"]]["source"]
    assert repo == {
        "source": "github",
        "repo": MARKETPLACE["owner"]["url"].split("github.com/")[1] + "/working-bee",
    }
    names = {e["name"] for e in ENTRIES}
    for plugin in settings["enabledPlugins"]:
        name, market = plugin.split("@")
        assert market == "working-bee" and name in names, plugin
    assert set(blocks[1]) <= names, "working-bee.json keys must be plugin names"


def test_bootstrap_assets_mentioned_in_the_skill_exist():
    text = (BOOTSTRAP / "SKILL.md").read_text(encoding="utf-8")
    for asset in re.findall(r"`(assets/[^`]+)`", text):
        assert (BOOTSTRAP / asset).is_file(), f"SKILL.md names a missing asset: {asset}"
