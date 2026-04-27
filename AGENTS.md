# AGENTS.md — instructions for AI agents working on JumlaOS

This file is the source of truth for AI coding agents (Devin, Claude Code,
Cursor, Copilot Workspace, …) contributing to JumlaOS.

## Non-negotiables

1. **Module boundaries are enforced.** Do not import from a sibling module
   (`mali` ↔ `talab` ↔ `makhzen`). Use `jumlaos.core.events` for async
   cross-module work, or a `jumlaos.core.services` interface for sync.

2. **Money stays in `BIGINT centimes`.** The helpers in
   `jumlaos.shared.money` are the only allowed conversion surface.

3. **Never commit secrets.** Use `.env.example` to document new env vars.
   CI runs `gitleaks`; a leaked key fails the build and rotates the key.

4. **No `Any`, `getattr`, `setattr` in new Python code.** Type everything.
   If a third-party library forces `Any`, wrap it in a thin typed adapter
   in `jumlaos.shared.adapters`.

5. **Never modify generated files by hand.** This includes Alembic
   migrations (edit the migration template instead), OpenAPI schemas,
   and zod codegen output.

6. **Never introduce a net-new dependency** without a one-line
   justification in the PR description.

## Style

- Python: ruff format + ruff check (config in `apps/api/pyproject.toml`).
- TypeScript: ESLint + Prettier; strict TS, no `any`, no `unknown` left
  dangling at module boundaries.
- Comments: terse. Describe *what the code does in general*, never the
  diff. If your comment only makes sense reading the PR, delete it.

## When adding a new HTTP endpoint

1. Pydantic request + response schemas in `<module>/schemas.py`.
2. Route in `<module>/routes.py`, mounted via `<module>/__init__.py`.
3. Permission check in a FastAPI dependency, not in the handler body.
4. Cross-tenant authz test in `tests/<module>/test_<route>.py`.
5. Happy-path + at least one failure-path test.
6. If the endpoint mutates state, write to `audit_log`.

## When adding a new DB table

1. SQLAlchemy model in `<module>/models.py`.
2. `business_id` FK + composite indexes on `(business_id, …)`.
3. Alembic autogen + review the migration line-by-line.
4. RLS policy `USING (business_id = current_setting('app.business_id')::bigint)`
   unless the table is explicitly cross-tenant (e.g. `users`).

## When adding a new background job

1. Procrastinate task in `<module>/tasks.py`.
2. Job payload must include `business_id`.
3. Worker-side assertion: `assert ctx.business_id is not None`.
4. Retries: max 5, exponential backoff capped at 1h.

## Testing

- Prefer property tests (`hypothesis`) for any monetary aggregator.
- Use the `db_session` fixture for DB tests; never roll your own engine.
- Network is forbidden in unit tests (`pytest-socket`). Use
  `respx` / `responses` for HTTP mocking.
