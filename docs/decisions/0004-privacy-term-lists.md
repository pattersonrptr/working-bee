# 0004. The privacy hook reads term lists kept outside the repository

Date: 2026-11-24. Status: accepted; amended by [ADR 0005](0005-privacy-asks-and-detects.md) (asks instead of
blocking, detectors, per-project approvals, default personal file).

## Context

`AGENTS.md` says hooks read nothing but the event JSON on stdin: anything else makes them depend on state that is
hard to see and to test. The `privacy` plugin has to know which words are sensitive (an employer, clients,
colleagues, private projects). That list is not in the event, and it must not be in the repository: committing
"never write X" publishes X.

## Decision

`guard_terms.py` is the documented exception. It reads two plain-text files, one term per line:

1. `<git common dir>/info/sensitive-terms`: per repository, never committed because it lives inside `.git/`. It
   is the same file `tools/privacy_check.py` already uses, so one list serves the hook and the pre-commit check.
2. The file in the plugin option `terms_file`: personal, for every project.

Rules that keep the exception narrow:

- Only those two paths, both chosen by the user; nothing is discovered or searched for.
- Messages never print a term: it is masked (`a***z`), and a location that contains one is hidden as well. The
  session brief only says how many terms are loaded.
- Terms shorter than 3 characters are ignored, since they would match almost anything.
- On a match the hook blocks (exit 2). An unexpected error lets the call through, like every other hook.

## Consequences

- Tests write their own term files in temporary folders and build the terms from split parts, so no real term is
  ever in the repository.
- Claude may still see a term it wrote itself. The guard stops terms from leaving through files, commits, pushes
  or publishing commands. It does not hide them from the conversation.
- Only `git commit`, `git push`, `gh`, `curl` and `wget` (and PowerShell's web cmdlets) are checked among shell
  commands. Searching for a term locally (`grep`) is allowed.
