# JumlaOS Pre-Release Security Checklist

Run this checklist before tagging any production release.

## Secrets
- [ ] `gitleaks detect --no-banner` — clean
- [ ] `git log -p | grep -iE 'AKIA|sk-|api[_-]?key|secret' ` — no hits
- [ ] All Fly + Cloudflare + Neon + Upstash secrets set, none using dev defaults
- [ ] `JUMLAOS_SECRET_KEY` is ≥32 chars and randomly generated
- [ ] `WHATSAPP_APP_SECRET` and `WHATSAPP_WEBHOOK_VERIFY_TOKEN` rotated for production

## Dependencies
- [ ] `pip-audit` — no critical/high vulns
- [ ] `pnpm audit --prod` — no critical/high vulns
- [ ] Renovate is enabled and weekly

## Authentication & authorization
- [ ] Login flow OK
- [ ] Logout flow OK
- [ ] Refresh-token rotation OK
- [ ] Cross-tenant authz tests passing (`pytest -k authz`)
- [ ] Cross-tenant data leak tests passing (`pytest -k tenant`)
- [ ] RBAC tests passing (owner / accountant / driver)
- [ ] All `/v1/*` endpoints except auth/health/webhook require `current_context`
- [ ] Module-gated endpoints reject when `modules_enabled[module] == false`

## Multi-tenant
- [ ] Postgres RLS enabled on every tenant-scoped table
- [ ] `app.business_id` set on every authenticated request
- [ ] Background jobs propagate `business_id`
- [ ] R2 paths scoped per business id

## Web/API hardening
- [ ] HTTPS-only (HSTS preload header set)
- [ ] Security headers verified: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- [ ] CORS allow-list = production origins only
- [ ] Cookies: `Secure`, `HttpOnly`, `SameSite=Lax` (or `Strict` where possible)
- [ ] CSRF Origin/Referer enforcement active
- [ ] Idempotency-Key middleware active on mutating routes
- [ ] Body size cap enforced (256 KiB API / 16 MiB webhooks)
- [ ] Rate limit verified on `/v1/auth/otp/request` and `/v1/auth/otp/verify`
- [ ] Swagger UI / OpenAPI hidden in prod

## Compliance (Morocco)
- [ ] Invoice numbering is gap-free per business per fiscal year
- [ ] Finalized invoices cannot be edited (DB trigger + service check)
- [ ] Invoice/payment audit log entries written for every mutation
- [ ] DGI export validated for the current fiscal year schema
- [ ] CNDP-compliant data residency (EU)
- [ ] Privacy policy + terms of service published
- [ ] Data export endpoint and data deletion endpoint documented

## Observability
- [ ] Sentry receiving events from API + web
- [ ] Logtail receiving structured logs
- [ ] Uptime monitor pinging `/v1/livez`
- [ ] Alert routing tested end-to-end

## Disaster recovery
- [ ] Backup restore tested in last 30 days
- [ ] Runbook for incident response published in `docs/runbooks/`

## Final go/no-go
- [ ] No open P0/P1 audit findings
- [ ] CI green on `main` and on the release tag
- [ ] Staging smoke tests green within last 24h
- [ ] Release notes + CHANGELOG entry published
