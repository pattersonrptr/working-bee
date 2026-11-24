---
name: gotcha
description: Records a surprise that cost time (a tool, library, platform or environment behaving unexpectedly) in docs/gotchas.md with symptom, cause, fix and the date it was verified. Use when a bug turned out to be a quirk rather than a code error, when a workaround was needed, when the user says "note this down" or "add a gotcha", or when the user runs /gotcha.
argument-hint: "[the surprise, or empty to use the one just solved]"
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Record a gotcha

Input: `$ARGUMENTS`. If empty, use the surprise just solved in this conversation. If none, ask.

A **gotcha** is a fact about the world that bit you (a tool, library, OS, API or environment). A **rule** is how to
behave in this project: if that is what this is, use `/memory:learn` instead. Often one surprise produces both: the
gotcha explains, and a one-line rule in `AGENTS.md` points to it.

## Steps

1. **Only what was verified.** Write what was observed and what fixed it. Mark guesses as guesses, or leave them
   out.
2. **Find the file.** `docs/gotchas.md`, unless `.claude/working-bee.json` sets `memory.gotchas`. If it does not
   exist, create it with the header below.
3. **Look for duplicates.** If an entry covers the same surprise, update it, including its date, instead of adding.
4. **Pick a section** by area (for example `## Tooling`, `## Database`, `## Windows`). Create one only if none fits.
5. **Write the entry** in this shape: a bold symptom, the date, then cause and fix in one or two sentences.

   ```markdown
   - **`python3` on Windows can be the Microsoft Store stub** (verified 2026-11-24). It exits 49 without running
     anything, so a hook launched with it silently does nothing. Fix: probe for a real Python first.
   ```

6. **Point to it** if agents must know it before acting: offer to add a one-line rule to `AGENTS.md` (for example,
   "Read docs/gotchas.md before touching the Docker setup").
7. Reply with one line: the entry title and the file.

## Header for a new file

```markdown
# Gotchas

Surprises that cost time. Each one: what happens, why, what to do. The date says when it was last verified.
```
