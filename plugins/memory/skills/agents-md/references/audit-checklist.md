# AGENTS.md audit checklist

Severity: **high** (will cause wrong or unsafe actions), **medium** (wastes effort or confuses), **low** (tidiness).

## Correctness (high)

1. **Commands that do not work:** a script missing from `package.json`, a tool missing from the dev dependencies,
   a wrong folder, a renamed file. Verify each command against the config.
2. **Paths that do not exist:** check every folder and file the text names (`git ls-files`).
3. **Contradictions:** between rules in one file, between AGENTS.md and CLAUDE.md, between levels (user
   `~/.claude/CLAUDE.md` versus the project), or between a rule and the settings (a rule says "ask before pushing"
   while `Bash(git push:*)` is allowed with no guard).
4. **Secrets or personal data** in any instruction file.

## Effectiveness (medium)

5. **Vague rules nobody can check:** "write clean code", "be careful", "follow best practices". Rewrite them as
   concrete actions or delete them.
6. **Rules that should be guards:** a prohibition whose violation is expensive (secrets, applied migrations,
   pushes to `main`, deploys) and that relies only on the text. Suggest the matching guard:
   - files that must not change once merged → `frozen_paths` in `.claude/working-bee.json` (working-bee core);
   - files whose edits need consent → `ask_paths` (file paths only, not commands);
   - commands that need consent (deploys, production CLIs) → a permission rule in `.claude/settings.json`:
     `"permissions": {"ask": ["Bash(npm run deploy:*)"]}`;
   - branches → `protected_branches` (core blocks commits and pushes).
7. **Length:** over ~150 lines, or long explanations inline. Move them to `docs/` and leave pointers.
8. **Stale facts:** versions, ports, team or process descriptions that the code or recent commits contradict.
9. **Missing basics:** no way to run the tests, no verification step before "done", no `Never` section.

## Tidiness (low)

10. Duplicated rules, inconsistent tone, sections in odd places, Claude-specific settings in AGENTS.md, or personal
    preferences in a project file.
