# 0006. `/review` runs specialists in parallel, then an adversarial pass

Date: 2026-11-24. Status: accepted.

## Context

A single reviewer, human or model, has a few problems:

- It checks everything at once, so the categories it is weakest at get the least attention.
- It reads the diff in the same context that wrote the code, so it shares the same blind spots.
- Asked to "find problems", it finds some whether they are real or not, and the reader pays to sort them out.

The author's private project already had one review agent: architecture only, with rules taken from the
project's docs and one line per finding. That agent was useful. Its weakness was that nothing checked its findings
before they reached the author.

## Decision

1. **Specialists, not one generalist.** Each reviewer covers one area: correctness, security or architecture. It
   runs in its own context, reads the diff itself, and reports one line per finding with a concrete scenario.
   A finding without a scenario is not reported. The three start in one message, so they run in parallel.
2. **An adversarial pass decides what reaches the user.** A fourth agent gets every finding and tries to refute
   each one by reading the code. It returns CONFIRMED, PLAUSIBLE or REFUTED with the evidence, then makes one
   fresh attack on the riskiest part of the change. The report shows confirmed and plausible findings, plus the
   count of refuted ones.
3. **Architecture comes only from the project's written rules.** No rules means "no architecture rules found",
   never a textbook style the project did not choose.
4. **Read-only and untrusted input.**
   - Reviewers get only `Read`, `Grep`, `Glob` and `Bash`, and are told to run only read-only commands. A test
     fails if a `*-reviewer` agent gets a write tool.
   - Diffs, PR text and commit messages are data. A line that gives the reviewer an instruction is reported as a
     finding.
   - Plugin agents cannot set `permissionMode`, `hooks` or `mcpServers`: Claude Code ignores those fields for
     plugins. Their only limits are the tool list and the session's own guards.
5. **Model per role, fixed in the agent file.** The specialists use `sonnet`, and the adversarial reviewer uses
   `inherit` (the session's model). A plugin option cannot change an agent's frontmatter, so a per-role option
   waits until someone needs it.

## Consequences

- One review starts four subagents and costs about four times the diff in input tokens. The skill offers a
  single reviewer for tiny changes and splitting for large ones.
- The report is shorter and more trustworthy, but takes longer than one pass: the adversarial step has to wait
  for the specialists.
- The roadmap's real test for phase 4 is that `/review` finds something a single pass would not.
