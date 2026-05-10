# Changelog

All notable changes to JumlaOS are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-beta] - 2026-05-10

### Launch label
**JumlaOS Mali Private Beta** — only the **Mali** module (credit ledger, invoicing, payments, DGI tax export) is shipped. **Talab** and **Makhzen** are gated behind per-business feature flags (`modules_enabled`) and are **disabled by default**. Analytics is unfinished and not exposed in the production UI.

### Added
- Mali MVP: debtors, debt events, payments, invoice generation, invoice PDF, DGI-ready tax export.
- Phone OTP auth, JWT cookie sessions, RBAC roles (owner / accountant / driver), Postgres RLS multi-tenant isolation.
- Cross-tenant authz integration tests.
- Audit log + outbox pattern, idempotency keys for mutating endpoints.
- WhatsApp Cloud API gateway with HMAC webhook signature verification.
- Background workers via Procrastinate (Postgres-backed queue).
- Health/readiness endpoints (`/v1/livez`, `/v1/readyz`, `/v1/health`).
- Rate limiting, request body size caps, CSRF Origin/Referer enforcement, secure security headers, prod-boot config validation (refuses to boot prod with dev secrets, default origins, default DB/Redis URLs, or `OTP_TRANSPORT=log`).
- CI: ruff, mypy, eslint, tsc, pytest, vitest, pip-audit, pnpm audit, gitleaks.
- Docs: architecture, security threat model, runbooks, ADRs.

### Resolved security/audit findings
- F02 idempotency middleware
- F04–F33 P1/P2 audit findings (PR #4)
- F09 webhook CSRF exemption
- F10/F20 phone-keyed rate limiting
- F11/F18/F29 comprehensive audit fixes (PR #5)
- F17 Swagger UI hidden in prod
- F21 prod-boot secret/infra hardening
- F25 request body size cap

### Hidden / not yet available
- **Talab** (WhatsApp order intake, voice/image triage, delivery routing) — routes return `status: "not_yet_enabled"` and are gated by `modules_enabled.talab`.
- **Makhzen** (inventory, multi-warehouse, expiry, demand forecast) — gated by `modules_enabled.makhzen`.
- **Analytics dashboards** beyond the basic Mali summary.

### Known limitations
- Real CMI / CashPlus billing integration requires production credentials and live HMAC validation tests in staging before public launch.
- Real Meta WhatsApp Cloud API requires a production phone number, app secret, and webhook subscription.
- Production R2 / Neon / Upstash / Sentry / Logtail / PostHog credentials must be provisioned before staging deployment (see `docs/deployment.md`).

[0.1.0-beta]: https://github.com/groupsmix/jumlaos/releases/tag/v0.1.0-beta
