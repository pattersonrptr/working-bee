# privacy

Keeps sensitive terms (your employer, clients, colleagues, private project names) out of what Claude writes,
commits, pushes and publishes. The lists of terms never enter the repository.

## Install

```
/plugin install privacy@working-bee
```

It depends on `core`, which is installed with it.

## Where the terms live

One term per line, `#` for comments, matched case- and accent-insensitively anywhere in the text. Terms shorter
than 3 characters are ignored.

| File | Scope | Why it is safe |
|---|---|---|
| `.git/info/sensitive-terms` | this repository | inside `.git/`, never committed |
| the plugin option `terms_file` | every project | a path you choose outside any repository |

Set the personal file with `/plugin` → privacy → configure, or `claude plugin configure privacy@working-bee`.

## What it checks

| When | What is checked |
|---|---|
| `Write`, `Edit`, `MultiEdit`, `NotebookEdit` | the new text and the path. An edit that keeps a term already in the file passes, so old files stay editable. |
| `git commit` | staged changes (with `-a`/`--all`, tracked changes too) and the command, which holds the message |
| `git push` | the diffs and messages of commits that are on no remote yet |
| `gh`, `curl`, `wget`, `Invoke-WebRequest`, `Invoke-RestMethod` | the command text: PR bodies, issue comments, payloads |
| session start | how many terms are loaded, never which (it warns when there are none) |

A match blocks the call. The message names the place (`notes.md:12`) and masks the term (`a***z`). Searching for a
term locally (`grep`) is allowed.

## Limits

- A term Claude wrote is still in the conversation. The guard stops it from leaving through these routes; it does
  not hide it from Claude.
- `git push` checks the current branch's unpushed commits, not other refs named in the command.
- Writes from other programs (a script Claude runs) are caught at `git commit`, not when they happen.

For a commit made outside Claude, add a pre-commit check. This repository's `tools/privacy_check.py` reads the
same `.git/info/sensitive-terms`.

Why the hook may read files at all: [ADR 0004](../../docs/decisions/0004-privacy-term-lists.md).
