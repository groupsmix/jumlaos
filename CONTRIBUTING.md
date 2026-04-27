# Contributing to JumlaOS

## Ground rules

1. **Follow the module boundaries.** `mali` may not import from `talab` or
   `makhzen` directly. Cross-module communication goes through
   `jumlaos.core.events` (domain events). See
   [`docs/architecture.md`](docs/architecture.md#module-boundaries).

2. **No silent failures.** Every error path has a log line, a metric, and
   a test.

3. **Every endpoint needs a cross-tenant authz test.** If you add
   `GET /v1/debtors/{id}`, you add a test that verifies a user from
   business A cannot read business B's debtors.

4. **Money is `BIGINT centimes`.** Never `float`, never `Decimal` at the
   storage layer. Conversion helpers live in `jumlaos.shared.money`.

5. **Times are always `TIMESTAMPTZ`.** Never naive datetimes.

6. **Never hard-delete financial data.** Use `deleted_at` soft-deletion.
   Morocco requires 10-year retention.

## Local dev

See [`README.md`](README.md#quick-start-local-dev).

## Branch + commit conventions

- Branches: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`.
- Commits: [Conventional Commits](https://www.conventionalcommits.org/):
  `feat(mali): add aging report`, `fix(core): reject duplicate phone on signup`.
- Keep PRs focused. One module, one concern.

## CI gates

CI runs on every push and must be green before merge:

- `lint`   — ruff + eslint + prettier
- `typecheck` — mypy + tsc
- `test`   — pytest + vitest
- `security` — gitleaks + pip-audit + pnpm audit
- `migrate-check` — `alembic upgrade head` followed by `alembic check`

## Writing migrations

```bash
cd apps/api
uv run alembic revision --autogenerate -m "add aging index"
uv run alembic upgrade head
```

Never edit a migration that has been merged to `main`. Write a follow-up
migration instead.

## Definition of Done

- [ ] Unit tests for the happy path and at least one failure path.
- [ ] A cross-tenant authz test if the change touches HTTP endpoints.
- [ ] Zero new ruff / mypy / eslint / tsc warnings.
- [ ] Relevant docs (`docs/`, module README) updated.
- [ ] PR description references a plan section or an issue.
