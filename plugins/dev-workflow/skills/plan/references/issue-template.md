# Issue body for one slice

Title: the slice title (imperative, under 70 characters).

```markdown
Part <n> of <k>: <goal in one line>.

## Why

<one line>

## Acceptance (tests first)

- [ ] Given ..., when ..., then ...
- [ ] ...

## Touches

<files or modules>

## Notes

- Size: S | M | L
- Depends on: #<issue> (or "nothing")
- Branch: `<type>/<issue>-<slug>`
- Approach and rejected options: <one line each, or a link to the plan file>
```

## Branch names

`<type>/<issue number>-<slug>`:

- `type` is `feat`, `fix`, `refactor`, `test`, `docs` or `chore`, as in Conventional Commits.
- `slug` is 2 to 5 lowercase words of the title, joined with hyphens.

Example: `feat/42-search-by-name`.

The issue number is only known after `gh issue create` returns. Write the body to a temporary file, create the
issue, then fix the branch line with `gh issue edit <n> --body-file <file>`. Or create every issue first and
fill in all the branch and dependency lines in a second pass.

## Privacy

Issues on a public repository are public. Before creating them, the plan text must not contain:

- names of people, clients or internal systems;
- data copied from production;
- secrets.

When the `privacy` plugin is on, it checks `gh` commands and asks before any of that leaves.
