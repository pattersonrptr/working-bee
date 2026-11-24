# Roadmap

> **working bee** (Australian and British English) is a mutirão: people who get together to do, for free, a job
> nobody would finish alone. Here the neighbours are agents, and the barn is your project.

Living document. Status on 2026-11-24: **phases 0, 1 and 2 done**; phase 3 built, waiting for the author's real test. The repository is public.

## 1. Goals

1. **Learn and master Claude Code by doing:** skills, hooks, subagents, plugins, marketplaces, orchestration,
   agent teams and evals. Each concept comes in because it solves a real need, not as a demo.
2. **Stop reconfiguring every project.** A new repository, or one without guardrails, is ready with a few lines of
   `.claude/settings.json` that only say which plugins to enable and with which options.
3. **Be free to share.** Generic, configurable plugins, documented in English, MIT licensed.
4. **Show AI fluency with evidence:** tests, evals with a baseline (with and without the plugin), token cost and
   recorded decisions (ADRs).

## 2. Principles (not negotiable)

- **Inspiration, never copying.** Ideas come from public documentation and from patterns seen in professional use
  of Claude Code. No code, text, internal names or processes are taken from proprietary sources.
- **Local first.** Commit locally; push and open PRs only after the change was validated running.
- **Defend every line.** Nothing goes in that the author cannot explain.
- **Privacy by default.** A privacy check runs from the first commit. Secrets, tokens and personal data never enter
  the repository, and personal settings are never turned into templates.
- **Hooks in standard-library Python.** On unexpected errors they let the call through (fail-open), except explicit
  guards. Every hook is tested as a real subprocess.
- **Lean skills.** `SKILL.md` is short; details live in `references/` and are read on demand. Context is expensive.
- **Docs in English**, with a `README.pt-BR.md` later.

## 3. Where things live (configuration levels)

| Level | Where | Applies to | What goes there |
|---|---|---|---|
| Managed | system policy | everyone, cannot be overridden | (company use, not applicable) |
| User | `~/.claude/` | all of the user's projects | personal taste: model, language, status line, voice |
| Project | `.claude/settings.json`, `AGENTS.md`, `.claude/skills/`, `.mcp.json` (committed) | whoever opens the repo | facts and rules of **that** repo, and which plugins to enable |
| Local | `.claude/settings.local.json`, `CLAUDE.local.md` (not committed) | you, only there | personal tweaks |
| **Plugin** | installed from a marketplace | wherever it is enabled (user or project) | reusable behavior: hooks, skills, agents, MCP servers, with options |

A plugin is a **package**, not a level: it lands at the level where it is enabled. A marketplace is a git catalog of
plugins. Rule of thumb: you would copy it to the next project → plugin; it only fits that repo → project; it is
personal taste → user.

**"Teams" for someone who works alone:** in a company, each team gets a plugin. Here each **hat** (stack or role)
gets one. A project switches on the hats it needs, and `core` comes along as everyone's dependency.

## 4. Architecture

```
working-bee/
├── .claude-plugin/marketplace.json      # catalog (name: "working-bee")
├── plugins/
│   ├── core/            # guardrails + session; every plugin depends on it
│   ├── memory/          # learn-from-mistakes, gotchas, agents-md
│   ├── bootstrap/       # /bootstrap: prepares a new repository
│   ├── dev-workflow/    # subagents + /plan /slice /review /deliver
│   ├── python-backend/  # Python hat (ruff, pytest, Django/FastAPI)
│   ├── privacy/         # personal data out of commits and context
│   ├── scraping/        # (phase 7) ethical collection
│   ├── infra-gcp/       # (phase 7) Terraform/gcloud with brakes
│   └── voice/           # (to decide) voice conversation skill, Windows only
├── evals/               # `claude plugin eval` suites, per plugin
├── tests/               # hook tests (subprocess) and manifest tests
├── tools/               # privacy check (pre-commit and CI)
├── docs/
│   ├── roadmap.md       # this file
│   ├── concepts.md      # map of Claude Code: what, when, where
│   ├── gotchas.md       # surprises that cost time, with verification dates
│   └── decisions/       # ADRs: one decision per file
├── AGENTS.md            # rules for agents working on this repo (Always / Ask first / Never)
├── CLAUDE.md            # contains only "@AGENTS.md"
├── .github/workflows/   # pytest (Linux, macOS, Windows) + claude plugin validate + privacy check
├── LICENSE              # MIT
└── README.md
```

**Dogfooding:** this repository uses its own plugins since phase 1.

### Plugin catalog

| Plugin | Components | Options | Origin |
|---|---|---|---|
| **core** ✅ | Hooks: dangerous commands, secret files, protected branches, frozen paths, "ask" for the guardrails' own config; session brief; git facts before compaction. Skill `/core:audit-settings` | protected branches; per project in `.claude/working-bee.json` | the author's own project hooks, generalized |
| **memory** ✅ | Skills `/memory:learn` (mistake → one-line rule in AGENTS.md), `/memory:gotcha`, `/memory:agents-md init\|audit\|update` | target file, gotchas file | the learn-from-mistakes idea |
| **bootstrap** ✅ | Skill `/bootstrap`: asks the stack and hats, writes AGENTS.md, CLAUDE.md, `.claude/settings.json` (marketplace + plugins + base permissions), `docs/gotchas.md`, PR template, privacy pre-commit (copy of `tools/privacy_check.py`) | none (YAGNI) | |
| **dev-workflow** | Agents: `planner` (read-only), `implementer`, `qa`, `architecture-reviewer` (reads the project's rules in `docs/`), `adversarial-reviewer`, a panel of analysts (pragmatic, sceptic, simple, security). Skills: `/plan` (plan → GitHub Issues → branches), `/slice` (tests-first slice → PR), `/review` (parallel reviewers + adversarial pass), `/deliver` (one worker per issue in a worktree), `/dependabot-triage`, `/quiz` (questions about the code for whoever must defend it) | model per role, minimum coverage | the author's project skills and agent, generalized |
| **python-backend** ✅ | Post-edit hook: `ruff check --fix` + `ruff format`. Test skill (detects poetry/uv/pytest) | runner (auto, venv, uv, poetry, path) | the author's project hook |
| **privacy** ✅ | Hook that asks before sensitive terms (lists outside the repo, [ADR 0004](decisions/0004-privacy-term-lists.md)) or personal data found by detectors ([ADR 0005](decisions/0005-privacy-asks-and-detects.md)) leave through writes, commits, pushes and `gh`/`curl` text; per-project approvals; `/privacy:terms` adds and suggests terms. The pre-commit comes from `/bootstrap` | personal terms file, detectors on/off | the author's privacy pre-commit hooks |
| **scraping** (phase 7) | Guardrails and skill for ethical collection: robots.txt, human pace, daily limits, personal data | limits | |
| **infra-gcp** (phase 7) | Hook: `terraform apply/destroy`, `gcloud ... create/delete` ask first; skill to review a Terraform plan | allowed projects | |
| **voice** (?) | Voice conversation skill (dictation + speech, pt/en, Windows) | voice, speed | the author's personal skill |

**Not included:** personal status line and settings (they stay in the author's personal config), project-specific
skills such as end-to-end runs, and third-party plugins.

## 5. Phases

Each phase ends with: behavior validated locally by the author; entries in `docs/gotchas.md` and ADRs for decisions;
`docs/concepts.md` updated; only then the push.

| Phase | Delivery | Concepts learned | Done when (real test) |
|---|---|---|---|
| **0. Foundation** | structure, `marketplace.json`, empty `plugins/core`, LICENSE, AGENTS.md, CI with `claude plugin validate` + pytest, first `docs/concepts.md` | marketplace, `plugin.json`, configuration levels, local `/plugin marketplace add` | `claude plugin validate .` passes; `/plugin install core@working-bee` works from the local path |
| **1. core** | guardrail hooks + brief + PreCompact + tests + options + `/audit-settings` | hooks (JSON on stdin, exit 2, `permissionDecision: ask`), matchers, `userConfig`, hook tests | a real project (Garimpei) drops its own guard hooks for `core@working-bee` without losing protection; a test shows every block happening |
| **2. memory** | `/learn`, `/gotcha`, `/agents-md` | skills: frontmatter, a `description` that triggers right, `argument-hint`, `allowed-tools`, `references/`; layered CLAUDE.md and `@import` | a project without instructions gets an AGENTS.md; a real mistake becomes a rule with `/learn`. **End of phase: history audit, then the repository can go public** |
| **3. bootstrap + hats** | `/bootstrap`, `python-backend`, `privacy` | plugin dependencies, `enabledPlugins` and `extraKnownMarketplaces` in a project, per-project options | a new repository is configured from scratch in 5 minutes; two private projects with personal data use `privacy` |
| **4. dev-workflow** | agents + `/plan`, `/slice`, `/review`, `/quiz`, `/dependabot-triage` | subagents (frontmatter, `tools`, `model`, `permissionMode`), context isolation, model per role, adversarial review, untrusted content (prompt injection) | a Garimpei feature goes from issue to PR through the flow; `/review` finds something a single pass would not |
| **5. Orchestration** | `/deliver` (parallel worktrees), background agents, an agent-team experiment | splitting and merging work, worktrees, `--bg` and `claude agents`, agent teams (experimental), scripted workflows | two Garimpei scrapers built in parallel, each in its own PR |
| **6. Quality and launch** | per-plugin evals with a baseline, token cost in the README, tagged versions, README with a GIF, `README.pt-BR.md`, CONTRIBUTING, launch post | `claude plugin eval` (ablation with/without the plugin), `claude plugin details`, `claude plugin tag`, releases | the README shows "improves X by Y points at Z tokens"; a stranger installs with 2 commands |
| **7. Optional** | `scraping`, `infra-gcp`, an original MCP server inside a plugin, `voice` | MCP in plugins, secret options | as needed |

### Status

| Phase | State |
|---|---|
| 0. Foundation | ✅ 2026-11-24 |
| 1. core | ✅ 2026-11-24, validated by the author in Garimpei |
| 2. memory | ✅ 2026-11-24: a private project got its AGENTS.md from `/memory:agents-md init`; a real mistake became a rule with `/memory:learn`; history audit clean |
| 3. bootstrap + hats | ⏳ built and tested headless; `privacy` validated by the author in two private projects (0.1.0, then 0.2.0 asks instead of blocking); waiting for a real `/bootstrap` |
| 4. dev-workflow | — |
| 5. Orchestration | — |
| 6. Quality and launch | — |
| 7. Optional | — |

## 6. Quality

- **Hooks:** one test file per hook, running the script as a subprocess with real event JSON. Every rule has a case
  that **must** block and one that **must** pass, with `WORKING_BEE_DEBUG=1` so a crash cannot pass as "allowed".
  A hook that reads the wrong interface (for example, environment variables that do not exist) looks exactly like
  one that works.
- **Manifests and frontmatter:** `claude plugin validate --strict` in CI, plus our own tests (kebab-case names,
  `description` with "Use when", no reserved names, dependencies that resolve, reference links that exist).
- **Evals (phase 6):** suites in `evals/` for skills with stable input and comparable output; manual binary checks
  for the rest. The "worth evaluating?" criteria go in an ADR.
- **Cost:** `claude plugin details` measures each plugin's token cost; it goes in the README.

## 7. Versions and distribution

- **Decided (ADR 0001):** semver from `0.1.0`, `claude plugin tag` for releases.
- Use in a project: `.claude/settings.json` declares `extraKnownMarketplaces.working-bee` (GitHub source) and
  `enabledPlugins`, so whoever trusts the folder is offered the install. Each machine still installs once
  (`claude plugin install <plugin>@working-bee --scope project`).

## 8. Risks and open questions

- **Agent teams** (checked 2026-11-24): they exist, are experimental and off by default
  (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). Phase 5 treats them as an experiment, with no promises.
- **Scripted workflows** (checked 2026-11-24): plugins can ship `workflows/*.js` (in the official plugin
  reference). To be studied in phase 5.
- ~~Python on Windows~~ **solved** (ADR 0002): `python3` was the Microsoft Store stub, which exits 49 and silently
  disables the guard. The `run.sh` launcher probes for and caches a real Python.
- ~~Per-project rules~~ **solved** (ADR 0003): `userConfig` is user-level, so project rules live in
  `.claude/working-bee.json`.
- **Proposal for core 0.2.0 (`ask_commands`):** ask before project commands (deploys, production CLIs) via
  `.claude/working-bee.json`. Today this is done with `permissions.ask` in settings.
- **Stop hook that suggests `/learn`:** not done (YAGNI). The skill already triggers on its own from its
  `description` after a correction.
- **Command audit log (PostToolUse) postponed:** a command log could keep secrets typed into commands. Revisit with
  the `privacy` plugin (phase 3).
- **Bee-themed plugin names** (such as `hive` for orchestration): leaning towards functional names, with the theme
  only in the README and the logo.
- **`voice`:** is a Windows-only skill worth publishing? Postponed on 2026-11-24, still open.

## 9. References

- Official documentation: plugins, marketplaces, hooks, skills, subagents (code.claude.com/docs).
- `claude plugin --help` (CLI 2.1.331): `validate`, `eval`, `configure`, `details`, `tag`, `init`, `prune`.
- Community marketplaces, for structure: the "awesome-claude-plugins" lists and claudemarketplaces.com.
