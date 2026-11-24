# Stack signals

Look at the root (and one level down for monorepos). A signal suggests a hat and, only when the command is
confirmed by the repository itself, permissions to allow.

| Signal | Stack | Hat | Allow (only if used) |
|---|---|---|---|
| `pyproject.toml`, `requirements*.txt`, `setup.py`, `uv.lock`, `poetry.lock` | Python | `python-backend` | `uv.lock`: `Bash(uv run pytest:*)`, `Bash(uv run ruff check:*)`. `poetry.lock`: `Bash(poetry run pytest:*)`, `Bash(poetry run ruff check:*)`. Otherwise: `Bash(python -m pytest:*)`, `Bash(ruff check:*)` |
| `package.json` | Node | none yet | the `test` and `lint` scripts it defines: `Bash(npm test:*)`, `Bash(npm run lint:*)` (or `pnpm`/`yarn`, per lock file) |
| `go.mod` | Go | none yet | `Bash(go test:*)`, `Bash(go vet:*)` |
| `Cargo.toml` | Rust | none yet | `Bash(cargo test:*)`, `Bash(cargo clippy:*)` |
| `*.tf` | Terraform | none yet (`infra-gcp` is planned) | `Bash(terraform fmt:*)`, `Bash(terraform validate:*)`. Never `plan` with real credentials, `apply` or `destroy` |
| `Makefile` | any | none | `Bash(make test:*)`, `Bash(make lint:*)` if those targets exist |

`privacy` fits any stack: suggest it when the project handles data about real people or belongs to an employer
or client.

Always fine to allow, read-only: `Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git log:*)`.
