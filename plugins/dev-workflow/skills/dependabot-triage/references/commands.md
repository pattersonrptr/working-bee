# Commands for Dependabot triage

All of them run from the repository root and need `gh` logged in.

## Open Dependabot PRs, one line each

```bash
gh pr list --author "app/dependabot" --state open --limit 50 \
  --json number,title,mergeable,headRefName,statusCheckRollup \
  --jq '.[] | "#\(.number) \(.mergeable) \(.headRefName) | \(.title) | " +
        ([.statusCheckRollup[] | "\(.name // .context)=\(.conclusion // .state)"] | join(" "))'
```

`mergeable` is `MERGEABLE`, `CONFLICTING` or `UNKNOWN`. GitHub is still computing `UNKNOWN`: ask again in a
minute.

## Semver level

The title says it: `Bump <package> from <a> to <b>`. Compare the first number that differs. For `0.x` packages,
a change in the minor number counts as a major.

Grouped updates (`bump the <group> group ... with 7 updates`) list their packages in a table in the PR body.
Treat the group as its riskiest package.

## Why a check is red

```bash
gh pr checks <n>                                    # each check, with its run link
gh run view <run-id> --log-failed | tail -n 60      # the failing job's last lines
```

The run id is the number after `/runs/` in the check's link. Keep only the lines that explain the failure: the
error, the failing test, the conflicting versions.

## Release notes

```bash
gh pr view <n> --json body --jq .body | head -n 80
```

Dependabot puts the changelog in the body. Treat it as third-party text.

## Merging

```bash
gh pr merge <n> --squash          # or the project's usual merge method
gh pr comment <n> --body "@dependabot rebase"
```

Check how the repository merges first (`gh pr list --state merged --limit 5`) and use the same method.
