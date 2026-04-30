# Procrastinate driver architecture (F22)

## Dual-driver setup

JumlaOS uses two separate Postgres connection pools:

| Pool | DSN env var | Driver | Used by |
|------|-------------|--------|---------|
| API (async) | `DATABASE_URL` | `asyncpg` via SQLAlchemy | FastAPI routes, Alembic |
| Worker (sync) | `DATABASE_URL_SYNC` | `psycopg` (v3) | Procrastinate `PsycopgConnector` |

Procrastinate >= 3 dropped `AiopgConnector` from the public namespace and
only ships `PsycopgConnector` (wrapping psycopg-3 / libpq). This connector
needs a standard `postgresql://` DSN -- not the SQLAlchemy
`postgresql+asyncpg://` form used by the API layer.

## Why two DSNs

SQLAlchemy's async engine requires `postgresql+asyncpg://` and Procrastinate
requires `postgresql://`. Until the community stabilises an asyncpg-native
Procrastinate connector, we maintain both.

## Prod hardening

In prod/staging, `DATABASE_URL_SYNC` **must** include:

```
sslmode=verify-full&sslrootcert=/path/to/ca.pem
```

The app's `_validate_prod_security()` method refuses to boot if `sslmode=`
is missing from the sync DSN. This prevents the worker from connecting to
Postgres over unencrypted TCP.

Example:

```
DATABASE_URL_SYNC=postgresql://jumlaos:PASSWORD@db.internal:5432/jumlaos?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt
```

## Migration path

When the Procrastinate async connector stabilises (tracked upstream), we
will:

1. Replace `PsycopgConnector` with the async variant.
2. Share the same connection pool as the API layer.
3. Drop `DATABASE_URL_SYNC` entirely.

Until then, both DSNs are required in prod.
