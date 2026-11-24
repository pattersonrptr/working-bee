# Pull request body for a slice

If the repository has `.github/pull_request_template.md`, fill that in and put the sections below under its
headings. Otherwise, use this:

```markdown
## What and why

<one paragraph: the slice and the issue it comes from>

## Tests first

Approved by the author on <date> in <commit>.

<details><summary>Red (before the code)</summary>

<the red summary from the approval commit's body>

</details>

<details><summary>Green (after)</summary>

<the green summary from the code commit's body>

</details>

## Verification

- QA: DONE (approved tests unchanged; criteria → tests; <check> ok)
- Review: <N confirmed fixed, N plausible left for later, N refuted>

Closes #<issue>
```

End with the Claude Code line, if the project's commits or PRs use one.

## Red, the right way

A good red fails **on an assertion**: the test runs and the result is wrong. A red caused by an import error or
a missing function proves less. Add a stub that returns an empty value to get a real assertion failure. When
only a `TypeError` or `ImportError` is possible (a function that does not exist yet), say so in the PR.

## Keep only the summary

Paste the lines that matter: the failing test names, one assertion message, and the totals. Never paste the
whole log. Logs may contain paths, environment values or data that should not be public.
