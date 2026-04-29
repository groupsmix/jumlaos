# JumlaOS audit — what is NOT yet fixed

Current status of every finding from `docs/audit/fix-audit.md` against the
codebase as of this branch (`devin/1777408327-audit-remaining-fixes`).

Status legend: ✅ done · 🟡 partial · ❌ not started · 🔒 needs human action

This file is the working backlog for the next audit-closure passes. When a
finding is fully closed, delete it from this file in the same PR.

---

## P0 — production blockers (closed in PR #2 / PR #3)

| ID  | Status | Where |
|-----|--------|-------|
| F01 | ✅ | `core/deps.py:59` — `set_config('app.business_id', :v, true)`. |
| F02 | ✅ | `main.py:144` — `idempotency_middleware` mounted; `INSERT … ON CONFLICT DO NOTHING RETURNING` in `core/idempotency.py`. |
| F03 | ✅ | `audit_outbox` written on caller session; `workers/tasks.py::drain_audit_outbox` drains. |
| F07 | ✅ | `OTP_TRANSPORT={whatsapp,sms,log}`; `workers/tasks.py::send_otp_whatsapp`/`send_otp_sms`; `shared/adapters/{whatsapp,sms}.py`. |
| F08 | ✅ | `auth.py:126,232` — per-phone `otp_lockout_until`; exponential backoff. |
| F09 | ✅ | `main.py::csrf_and_context` — default-deny on missing Origin+Referer; webhook prefix exemption; `SameSite=Strict` on access cookie. |
| F10 / F20 | ✅ | `core/rate_limit.py` — slowapi + Redis; per-route policies on `auth.py` and `whatsapp/routes.py`. |
| F11 | ✅ | `alembic/versions/20260427_0003_triggers.py` — append-only triggers on `debt_events`, `payments`, `invoices`. |
| F15 | ✅ | `core/idempotency.py` — composite `(business_id, user_id, key)` unique; `INSERT … ON CONFLICT … RETURNING`; failed status preserved. |
| F19 (refresh) | ✅ | `auth.py:284,360-371` — `family_id` on `RefreshToken`; reuse → revoke family + `auth.refresh.reuse_detected` audit. |
| F28 | ✅ | `workers/tasks.py::check_ledger_drift` periodic + property test. |

## P1 — production-readiness

| ID  | Status | Notes |
|-----|--------|-------|
| F04 | ❌ | No `migrate-check` CI job. Need: postgres service container running `alembic upgrade head` → `alembic check` → `alembic downgrade base`. Block merges. |
| F05 | ❌ | No `scripts/check_module_boundaries.py`; no CI job enforcing the doc-claimed module boundaries. |
| F06 | ❌ | Coverage omits in `pyproject.toml` still hide `whatsapp/routes.py`, `talab/*`, `makhzen/*`, `billing/*`, `analytics/*`, `main.py`-equivalents. No `fail_under`. No per-module floors. |
| F12 | ✅ | `infra/fly/api.fly.toml` + `worker.fly.toml`; `docs/runbooks/ha.md`. |
| F13 | ✅ | `workers/context.py::with_business_context` + `assert_bound`; tests in `tests/test_worker_context.py`. |
| F14 | ✅ | `core/routes/health.py` — `/livez` + `/readyz` checking Postgres + Procrastinate + Redis + R2 with 500 ms timeouts; race fixed (PR #3). |
| F21 | ✅ | `config.py::_validate_prod_security` — refuses default DB/Redis/origins/OTP transport/R2 bucket and partial R2 quad. |
| F23 | ❌🔒 | Need: `.github/workflows/deploy.yml` (gated on `ci`, `workflow_dispatch`, OIDC + Fly token). Branch protection rules + linear-history + dismiss-stale-reviews are **GitHub UI / API** actions the repo admin must apply. |
| F25 | ✅ | `main.py::body_size_limit` — 256 KB JSON / 16 MB webhook caps via `Settings.max_request_bytes` / `max_webhook_bytes`. |
| F30 | 🟡 | One placeholder test (`tests/integration/test_authz.py`) exists. Need: `crosstenant_runner` fixture + a test per Mali route, asserting 404 (not 403). CI gate: `count(authz_tests) >= count(mali_routes)`. |
| F31 | ❌ | `apps/web/next.config.mjs` uses `@ducanh2912/next-pwa` defaults; no `runtimeCaching` rules excluding `/v1/*`. PWA may serve stale auth-bearing responses across users. |
| F32 | ❌ | `apps/web/next.config.mjs` only sets `X-Frame-Options`/`X-Content-Type-Options`/`Referrer-Policy`/`Permissions-Policy`. No CSP at all. |

## P2 — should-fix (60–90 days)

| ID  | Status | Notes |
|-----|--------|-------|
| F17 | ✅ | `main.py:152` — `docs_url=None`/`openapi_url=None` when `is_prod`. |
| F18 | ✅ | OtpCode attempts now go through the same outbox-style write as F03; no lost increments. |
| F19 (cleanup) | ❌ | No periodic task deleting `otp_codes` / `domain_events.processed_at` rows. Audit-log retention policy undocumented. |
| F22 | ❌ | No `docs/runbooks/db-driver.md` documenting the asyncpg + psycopg dual-driver story. `database_url_sync` does not assert `sslmode=verify-full` in prod. |
| F24 | ❌🔒 | No trivy job, no CycloneDX SBOM, no cosign signing, base image not pinned by digest. (Cosign keyless requires repo OIDC trust setup — partly human action.) |
| F26 | ❌ | `webhook_dlq` table exists; no `whatsapp.replay_dlq(id)` Procrastinate task; no `python -m jumlaos.scripts.replay_dlq` CLI. |
| F27 | ❌ | `domain_events.processed_at` is still a single boolean — no per-subscriber offsets / `event_subscriber_offsets` table. |
| F29 | 🟡 | `shared/ids.py::new_uuid` exists but external IDs still use `BIGINT` PKs. Tax IDs (`ice_number`, `rc_number`, `if_number`, `cnss_number`, `dgi_taxpayer_id`) stored in plaintext on `Business`. |
| F33 | ❌ | `logging.py` writes raw phones / IPs. No HMAC-with-pepper redaction processor; no documented retention window. |

## Quick wins (§7 of the audit)

| Item | Status |
|------|--------|
| Add `migrate-check` CI job (F04). | ❌ |
| Drop coverage omits + re-baseline `fail_under` (F06). | ❌ |
| Replace `text(f"…")` for `app.business_id` with `set_config(...)` (F01). | ✅ |
| `app.middleware("http")(idempotency_middleware)` in `main.py` (F02). | ✅ |
| Body-size limit middleware (F25). | ✅ |
| `Cache-Control: no-store` on all `/v1/*` except `/livez`/`/readyz`/`/health`. | ✅ (`main.py::secure_headers`) |
| Assert non-default `JUMLAOS_ALLOWED_ORIGINS` in `_validate_prod_security` (F21). | ✅ |
| Fail prod boot if `redis_url` looks like default localhost (F21). | ✅ |
| Pre-commit config + document `pre-commit install` in CONTRIBUTING. | 🟡 (config exists; doc still missing). |
| Smoke test: boot all-default and assert 5xx unless `JUMLAOS_SECRET_KEY` is the only thing set. | ❌ |
| Check in `scripts/check_module_boundaries.py` (F05). | ❌ |
| Fly autoscaling 1–4 for the API. | ✅ (`infra/fly/api.fly.toml`). |
| `permissions: contents: read` on `ci.yml`. | ❌ |
| Disable `/v1/docs` in prod (F17). | ✅ |

## Items requiring repo-admin / infra action

These cannot be closed by code alone. Listed so the human owner can plan them:

- **F23** — branch protection: enable on `main` (require all CI green, linear
  history, code review, dismiss stale reviews on push, no force-push).
  Add Fly OIDC role + scoped deploy token + the `FLY_API_TOKEN` repo secret
  before `deploy.yml` will work in CI.
- **F24** — cosign keyless requires the repo OIDC issuer to be trusted by
  Sigstore Fulcio (default works for public repos; private repos need extra
  config).
- **F29** — encryption keys: provision a KMS-backed key (or Fernet pepper
  stored in Fly secrets) before flipping the encryption migration on.
