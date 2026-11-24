---
name: terms
description: Adds, suggests or counts the sensitive terms (names of people, teams, clients, internal codenames and hosts) that the privacy hook keeps out of files, commits and pushes, without ever printing the lists. Use when the user says to add or protect a name ("adiciona X na lista", "don't let X go public"), when a name the user would likely not want public shows up in the work (a colleague, a family member, an internal project or client), when the user asks what should be protected, or when the user runs /privacy:terms.
argument-hint: "add <term> [--repo] | suggest | count"
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git log:*), Bash(git ls-files:*), Bash(bash *terms_cli.py*)
---

# Sensitive terms

Input: `$ARGUMENTS`. All changes go through the CLI, which never prints a list:

```
bash "${CLAUDE_PLUGIN_ROOT}/hooks/run.sh" terms_cli.py add [--repo] "<term>" ["<term>" ...]
bash "${CLAUDE_PLUGIN_ROOT}/hooks/run.sh" terms_cli.py check "<candidate>" ...
bash "${CLAUDE_PLUGIN_ROOT}/hooks/run.sh" terms_cli.py count
```

Never read, print or quote the list files (`.git/info/sensitive-terms`, `~/.config/working-bee/...`).

## add

Personal list by default: it applies to every project (people, employer-internal names, home address). Use
`--repo` for names that only matter in this repository (a client of this project, a patient, a contact). If the
scope is unclear, ask in one line. Confirm with the CLI's masked output.

## suggest

1. Look at what is in play: the text written in this conversation, `git diff` and `git diff --cached`, and files
   changed recently. Do not open data, dumps or `.env`.
2. Pick candidates in the categories the user cares about: people (colleagues, managers, family), team names,
   internal codenames and systems, non-public clients or partners, internal domains and servers, street or
   building names. Skip public facts the user is fine sharing (an employer's or a product's public name) and
   anything a detector already catches (e-mails, phones, CPF, CEP, private IPs, `.local`/`.corp` hosts).
3. Drop the ones `check` says are covered.
4. Ask once, multi-select, with the scope (personal or this repository) for each; add only what the user picks.
   Never add a guess the user did not choose.

## count

Run `count` and report the two numbers.

## When something must be published on purpose

A repository that should publish some of it (a resume with your own e-mail and phone) allows it in
`.claude/working-bee.json`: `{"privacy": {"allow": ["email", "phone"], "allow_terms": ["<your name>"]}}`.
Detector names: `email`, `phone`, `cpf`, `cnpj`, `cep`, `address`, `host`, `ip`. Editing that file asks the
user; propose it, never apply it silently.
