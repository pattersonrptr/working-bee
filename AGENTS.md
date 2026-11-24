# working-bee — rules for agents

A Claude Code plugin marketplace. Plugins live in `plugins/<name>/`; the catalog is `.claude-plugin/marketplace.json`.
Read `PLAN.md` (roadmap and status) and `docs/concepts.md` (how Claude Code fits together) before planning.

## Commands

- Tests: `python -m pytest -q`
- Manifests: `claude plugin validate . --strict` and `claude plugin validate plugins/<name> --strict`
- Privacy check: `python -I tools/privacy_check.py --all` (runs as pre-commit once `git config core.hooksPath .githooks`)

## Always

- Hooks are Python 3.9+, standard library only, run through `plugins/core/hooks/run.sh`.
- Every hook rule gets a test that **must block** and one that **must pass**, running the hook as a subprocess with real event JSON.
- Hooks fail open on unexpected errors (`WORKING_BEE_DEBUG=1` re-raises), except explicit guards.
- Docs, code and commit messages in English. Keep `SKILL.md` short; details go in `references/`.
- A surprise that cost time goes to `docs/gotchas.md` (with the date it was verified); a decision goes to `docs/decisions/`.
- Bump the plugin's `version` when its behavior changes.

## Ask first

- Pushing, opening PRs, publishing or tagging releases.
- Adding a plugin, a dependency, or a network call.
- Loosening a guard's default (fewer blocks, fewer prompts).

## Never

- Copy code, text, names or processes from proprietary sources, including the author's employer. Public documentation and original work only.
- Commit secrets, personal data or private names (the privacy check enforces it; never `--no-verify`).
- Write hooks that block everything on unexpected input, or that read anything but the event JSON on stdin.
