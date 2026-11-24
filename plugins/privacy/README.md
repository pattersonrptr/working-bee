# privacy

Asks before sensitive terms (people, teams, clients, internal codenames) or personal data (e-mails, phones, CPF,
CNPJ, CEP, addresses, internal hosts, private IPs) leave through what Claude writes, commits, pushes or publishes.
Only you can approve. The term lists never enter the repository.

The idea: a public fact is not a secret (your employer is on your resume). What matters is that nothing leaves
without your OK. Why it asks instead of blocking: [ADR 0005](../../docs/decisions/0005-privacy-asks-and-detects.md).

## Install

```
/plugin install privacy@working-bee
```

It depends on `core`, which is installed with it. It works with no setup: the detectors need no list.

## What it finds

| Kind | How |
|---|---|
| Your terms | names you listed: colleagues, family, teams, codenames, clients. Case- and accent-insensitive, anywhere in the text. |
| `email` | any address except example, test and noreply ones |
| `phone` | Brazilian numbers with `+55` or `(DD)`, or after a label (`tel`, `celular`, `whatsapp`) |
| `cpf`, `cnpj` | formatted, or bare digits after the label; check digits must be valid |
| `cep` | after the label `CEP` |
| `address` | `Rua`, `Avenida`, `Travessa`... + a proper name + a number; `Condomínio`, `Residencial`, `Edifício` + a name |
| `host` | internal names: `*.local`, `*.internal`, `*.corp`, `*.intranet`, `*.lan` (not files such as `.env.local`) |
| `ip` | private addresses: `10.x`, `172.16-31.x`, `192.168.x` |

## Where it looks

| When | What is checked |
|---|---|
| `Write`, `Edit`, `MultiEdit`, `NotebookEdit` | the new text and the path. An edit that keeps something already in the file passes. |
| `git commit` | staged changes (with `-a`/`--all`, tracked changes too) and the message |
| `git push` | diffs and messages of commits that are on no remote yet |
| `gh`, `curl`, `wget`, `Invoke-WebRequest`, `Invoke-RestMethod` | the command text: PR bodies, issue comments, payloads |
| session start | how many terms are loaded and which detectors are on, never which terms |

A finding opens the permission prompt with the place (`notes.md:12`) and the kind (`a CPF`, `sensitive term
a***z`), never the value. Searching locally (`grep`) is never checked.

## Your terms

Say it in the conversation: "add Maria to the sensitive list", or run `/privacy:terms`:

| Command | What it does |
|---|---|
| `/privacy:terms add <term>` | adds to your personal list, used in every project (`--repo`: only this repository) |
| `/privacy:terms suggest` | looks at the current work for names you may not want public and lets you pick |
| `/privacy:terms count` | how many terms each list has |

The lists are plain text, one term per line, and are never printed:

| File | Scope |
|---|---|
| `~/.config/working-bee/sensitive-terms.txt` (or the plugin option `terms_file`) | every project |
| `.git/info/sensitive-terms` | this repository; inside `.git/`, never committed |

## Publishing on purpose

A repository that should publish some of it, such as your resume, says so in `.claude/working-bee.json`:

```json
{
  "privacy": {
    "allow": ["email", "phone"],
    "allow_terms": ["Your Name"]
  }
}
```

The file is committed, so the exception is visible, and editing it always asks you. The plugin option `detectors`
turns all detectors off for you, everywhere.

## Limits

- Claude still sees what it wrote. The guard controls what leaves, not the conversation.
- Names in prose that no list knows are not found. `/privacy:terms suggest` helps build the list.
- `git push` checks the current branch's unpushed commits, not other refs named in the command.
- Writes by programs Claude runs surface at `git commit`, not when they happen.
- With no one to ask (`claude -p`), a finding stops the call.

For commits made outside Claude, add the pre-commit check: `/bootstrap` offers it.
