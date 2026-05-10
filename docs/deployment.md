# JumlaOS Deployment Guide

This guide covers deploying JumlaOS to **staging** and **production**. Local development is documented in the root `README.md`.

## Architecture

- **API**: Fly.io app (`jumlaos-api`), one or more machines + a worker process running Procrastinate.
- **Web**: Cloudflare Pages, build target `apps/web`, output `.next` (Edge runtime where possible).
- **Database**: Neon Postgres 16, EU region (Paris/Frankfurt), `sslmode=require`.
- **Redis**: Upstash Redis 7, EU region, TLS.
- **Object storage**: Cloudflare R2 bucket (`jumlaos-prod` / `jumlaos-staging`).
- **Email**: Resend or Postmark, domain `jumlaos.ma`, DKIM + SPF + DMARC.
- **Observability**: Sentry, Logtail, Grafana Cloud, PostHog EU.

## Environments

| Env       | URL                          | Branch  | Auto-deploy |
| --------- | ---------------------------- | ------- | ----------- |
| dev       | localhost                    | any     | n/a         |
| staging   | https://staging.jumlaos.ma   | `main`  | yes         |
| prod      | https://jumlaos.ma           | tags    | manual      |

## Required secrets (production)

The API refuses to boot in `prod` / `staging` if any of these are missing or use dev defaults — see `apps/api/src/jumlaos/config.py`.

```
JUMLAOS_ENV=prod
JUMLAOS_SECRET_KEY=<32+ char random>
JUMLAOS_ALLOWED_ORIGINS=https://jumlaos.ma
DATABASE_URL=postgresql+asyncpg://...neon.tech/...sslmode=require
DATABASE_URL_SYNC=postgresql://...neon.tech/...sslmode=require
REDIS_URL=rediss://...upstash.io:6379
OTP_TRANSPORT=whatsapp
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_APP_SECRET=...
WHATSAPP_WEBHOOK_VERIFY_TOKEN=<random>
R2_ENDPOINT=https://<account>.r2.cloudflarestorage.com
R2_BUCKET=jumlaos-prod
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
SENTRY_DSN=...
```

Set these via `fly secrets set -a jumlaos-api KEY=value` (API) and Cloudflare Pages → Settings → Environment variables (web).

## First-time deployment

1. Provision Neon database, get connection strings.
2. Provision Upstash Redis, get TLS URL.
3. Provision R2 bucket and access keys.
4. Set Fly secrets.
5. `fly deploy -a jumlaos-api -c infra/fly.api.toml`
6. Run migrations: `fly ssh console -a jumlaos-api -C 'uv run alembic upgrade head'`
7. Push to Cloudflare Pages.
8. Configure DNS (`jumlaos.ma`, `api.jumlaos.ma`).
9. Smoke test `/v1/livez`, `/v1/readyz`, login flow.

## Migrations

```
uv run alembic upgrade head     # forward
uv run alembic downgrade -1     # rollback one revision
```

Always run migrations **before** the new API code goes live. Migrations must be backward-compatible with the previous code revision.

## Backups

Neon takes automated PITR snapshots every 24h with 7-day retention on the free tier; upgrade to a paid plan for the **10-year DGI retention** requirement before going public.

Manual logical backup:

```
pg_dump --format=custom --file=jumlaos-$(date +%F).dump "$DATABASE_URL_SYNC"
```

Restore:

```
pg_restore --clean --if-exists --dbname="$DATABASE_URL_SYNC" jumlaos-YYYY-MM-DD.dump
```

Test restore quarterly into a disposable Neon branch.

## Rollback

1. `fly releases -a jumlaos-api` to find the previous release id.
2. `fly deploy -a jumlaos-api --image registry.fly.io/jumlaos-api:<previous-tag>`.
3. If a destructive migration shipped, restore from PITR to the timestamp before the deploy.

## Smoke tests

After every prod deploy:

- `curl https://api.jumlaos.ma/v1/livez` → 200
- `curl https://api.jumlaos.ma/v1/readyz` → 200
- Login with a test phone, verify OTP, hit `/v1/me`, list debtors.
- Generate one invoice PDF and confirm bilingual rendering.
- Send a Meta webhook ping and confirm signature validation logs success.

## Monitoring & alerts

- Sentry alerts on error rate > 1% over 5 minutes.
- UptimeRobot pings `/v1/livez` every 60 seconds.
- Grafana dashboard: request latency p95, DB pool saturation, queue depth.
- Logtail saved search: `level=error` paged to on-call.
