# 0001. Semantic versions from the first release

Date: 2026-11-24. Status: accepted.

## Context

A plugin either declares a `version` in `plugin.json` or is identified by the git commit it was installed from.

- Without `version`, every commit reaches whoever installed it on the next update. Simple, but users get changes
  they did not choose, and `claude plugin validate --strict` (which CI runs) warns about the missing field.
- With `version`, users stay on that version until it changes, and `claude plugin tag` can create a
  `{name}--v{version}` release tag after checking that `plugin.json` and the catalog agree.
- While developing from a local-path marketplace, the version pin is ignored: edits apply on the next session.

The plan leaned towards commit SHAs while the repository is private and semver once it opens.

## Decision

Every plugin starts at `0.1.0` and follows semver: patch for fixes, minor for new behavior or options, major for
removals or behavior that blocks more than before. Major stays at 0 until the repository is public and the plugin
has been used in at least two projects.

## Consequences

- One scheme from the start: no migration when the repository opens, and strict validation passes.
- Each behavior change needs a version bump (a rule in `AGENTS.md`).
- Local development is unaffected, because local paths ignore the pin.
