# Writing rules that work

A rule in `AGENTS.md` is read at the start of every session, by every agent, alongside many others. It has to be
understood in one reading and checked without judgment.

## Shape

- **One line.** If it needs a paragraph, it is documentation: put it in `docs/` and add a one-line pointer
  ("Before changing X, read docs/x.md").
- **Imperative and concrete.** Name the command, file, value or situation.
- **Reason after a colon or dash** when the rule looks arbitrary. Agents follow rules they understand more
  reliably, and a reason tells a future reader when the rule no longer applies.
- **Positive where possible.** "Use `uvx poetry@2 run`" beats "don't call `.venv/Scripts/python`": it says what to
  do. Keep "never" for real prohibitions.
- **Date decisions** that may be revisited: `(decided 2026-11-24)`.

## Examples

| Mistake | Weak rule | Strong rule |
|---|---|---|
| Ran tests from the wrong folder | Run tests correctly. | Run backend tests from `backend/` with `poetry run pytest src/tests`. |
| Changed an applied migration | Be careful with migrations. | Never edit a migration already on `main`: add a new one. |
| Parsed a timestamp as local time | Watch out for timezones. | The API sends naive UTC timestamps: parse them as UTC. |
| Used `role="alert"` selectors | Selectors can be tricky. | Select form errors by `.form-error`, not by role: Next.js has its own `role="alert"` announcer. |
| Asked too many questions | Ask fewer questions. | For copy and styling, decide and mention it; ask only about behavior and data. |

## Placement

| Section | For |
|---|---|
| `Always` | Habits that apply to every task (verification commands, commit format) |
| `Ask first` | Actions that are fine with consent (pushes, new dependencies, schema changes) |
| `Never` | Prohibitions; consider a hook or permission rule for the expensive ones |
| Area sections (`Commands`, `Tests`, `Known traps`...) | Rules that only matter in one part of the work |

## Keep the file healthy

- Before adding, search for an overlapping rule and merge into it.
- If the file passes ~150 lines, suggest `/memory:agents-md audit` to prune.
- A rule that was broken twice even though it was clear is a candidate for a hook.
