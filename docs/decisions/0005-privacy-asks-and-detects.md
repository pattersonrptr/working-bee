# 0005. Privacy asks instead of blocking, and detects personal data with no list

Date: 2026-11-24. Status: accepted. Amends [ADR 0004](0004-privacy-term-lists.md) (where the lists live is
unchanged).

## Context

Privacy 0.1.0 blocked every sensitive term. Testing it on two private projects raised two problems:

- **A public fact is not a secret.** An employer's name is on the author's LinkedIn and belongs in a public
  resume. What must not leave is narrower: internal codenames, teams, colleagues, family, non-public clients,
  internal hosts, addresses, and how a product works inside. A name blocklist cannot tell these apart. Rajiv Pant
  reached the same conclusion in public ("the secret isn't the name, it's the approval"): blocklists flag public
  bios, and people end up turning the guard off.
- **A list nobody fills protects nothing.** The author expected protection without having to type lists.

Prior art checked on 2026-11-24: Sensitive Canary (Claude Code plugin: PII rules with check digits and
labels near the noisy ones, per-category allow tags), a Classmethod write-up (stdlib hook: format plus checksum,
example domains excluded, never echo the value), gitleaks (allowlists and stopwords), Microsoft Presidio (deny
lists as recognizers). None of them checks commits and pushes from the agent's side with per-project approvals.

## Decision

1. **Ask, do not block.** A finding returns `permissionDecision: "ask"` with a masked reason. Only the user can
   approve, so "unless I say so explicitly" is the permission prompt. Without a person (`claude -p`) the call
   does not run.
2. **Detectors that need no list:** e-mail (example, test and noreply addresses excluded), phone, CPF and CNPJ
   (check digits), CEP, street and building addresses, internal hosts (`.local`, `.corp`, `.internal`...) and
   private IPs. The noisy ones fire only next to a label (`tel`, `CEP`, `CPF` for bare digits) or a strong format
   (`+55`, `(11)`). Measured on two repositories (690 tracked files): no false positive left after excluding
   dotfiles such as `.env.local`, and 6 real e-mails.
3. **Approvals that last, per repository:** `.claude/working-bee.json` → `privacy.allow` (detector names) and
   `privacy.allow_terms` (terms this repository publishes on purpose). The file is committed and reviewed, so the
   approval is visible. Every edit to it asks the user (core's `ask_paths`).
4. **Terms without a text editor:** `/privacy:terms add|suggest|count`. Its CLI appends and checks terms but never
   prints a list. The personal list defaults to `~/.config/working-bee/sensitive-terms.txt`, so the plugin option
   is optional.
5. **What a filter cannot see** (how an employer's product works inside) is a rule for the agent, in the user's
   own `~/.claude/CLAUDE.md`, not a pattern.

## Consequences

- AGENTS.md says "loosening a guard needs the author's OK": this change was asked for by the author on
  2026-11-24.
- An approval in the prompt is not remembered. Repeated approvals in one repository are a sign to add an `allow`
  entry there.
- `allow_terms` writes a term into a committed file, which is fine only because that repository publishes it
  anyway.
- Still out of reach: names in prose that no list knows, other ways out (e-mail, chat, the clipboard), and
  writes by programs Claude runs, which surface only at `git commit`.
