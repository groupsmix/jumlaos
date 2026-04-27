# JumlaOS architecture

## Shape

**Modular monolith.** One deploy unit, one DB connection pool, one set of
credentials, one log stream. Module boundaries are enforced by Python
imports (and a CI check) — not by network calls.

```
apps/api/src/jumlaos/
├── core/         auth, tenancy, audit, RBAC, domain_events, health
├── mali/         debtors, debt events, invoices, payments, tax periods
├── talab/        WhatsApp ingest, order triage, orders, deliveries  [stub]
├── makhzen/      products, stock lots, movements, warehouses        [stub]
├── analytics/    KPI rollups, materialized-view refresh             [stub]
├── whatsapp/     Meta Cloud API gateway, templates, parser
├── billing/      CMI + CashPlus subscriptions
├── shared/       money, phone, fuzzy match, retries, time, fixtures
└── main.py       app factory — mounts routers and middleware
```

### Module boundaries

- **Hard rule:** `mali`, `talab`, `makhzen`, `analytics` do **not** import
  from each other.
- Cross-module wiring goes through `jumlaos.core.events` (an append-only
  `domain_events` table + Procrastinate workers) or through narrow,
  well-typed service interfaces in `jumlaos.core.services`.
- A CI step (`scripts/check_module_boundaries.py`) walks the import graph
  and fails the build on a violation.

### Request lifecycle

```
Cloudflare → Fly.io proxy
           → FastAPI app
             ├─ middleware: request_id, logging, CORS
             ├─ auth dependency: verify JWT cookie, set ContextVar(user_id)
             ├─ tenancy dependency: set ContextVar(business_id)
             │                      + SET LOCAL app.business_id (RLS)
             ├─ RBAC dependency:    role + permission check
             └─ handler: pure business logic
```

Everything under `/v1` requires auth **except** `/v1/auth/*`, `/v1/health`,
`/v1/ready`, and signed webhooks.

### Data model principles

- All money is `BIGINT centimes`. Helpers in `jumlaos.shared.money`.
- All times are `TIMESTAMPTZ`. Helpers in `jumlaos.shared.time`.
- Financial tables (`debt_events`, `invoices`, `payments`, `tax_periods`)
  are **append-only**. Corrections go through a signed reversal row, never
  a mutation.
- Soft-delete (`deleted_at`) on tenant-scoped tables. Hard-delete is
  forbidden on anything with money in it (10-year DGI retention).
- Projections (`debt_balances`, `stock_levels`) are derived from the
  append-only ledgers and recomputable from scratch.

### Multi-tenant isolation

Two layers, both required:

1. **Postgres Row-Level Security.** Every tenant-scoped table has a policy
   `USING (business_id = current_setting('app.business_id')::bigint)`.
   The tenancy dependency issues `SET LOCAL app.business_id = :id` on
   every request.
2. **FastAPI dependency.** The handler receives an already-bound
   `BusinessContext` object and cannot escape it without an explicit
   `run_as_cross_tenant` helper that logs to the audit log.

### Events

`core.events.publish(kind, payload)` writes to `domain_events` in the same
transaction as the state change. A Procrastinate worker fans events out
to subscribers. Examples:

- `OrderConfirmed` → `mali.invoicing.draft_from_order`,
  `makhzen.stock.reserve`
- `PaymentRecorded` → `mali.reminders.cancel_for`
- `ExpiryBreached` → `whatsapp.alerts.notify_owner`

### Background work

- One Procrastinate queue, tagged per module.
- Workers run in the same Docker image as the API with a different entrypoint.
- Retries: max 5, exponential backoff capped at 1h.
- A dead-letter table (`webhook_dlq`) captures anything that exhausts retries.

### Observability

| Signal | Sink |
|---|---|
| Errors | Sentry |
| Structured logs | Logtail (JSON-per-line) |
| Metrics | Grafana Cloud (Prometheus-compatible) |
| Product analytics | PostHog EU |
| Traces | OpenTelemetry → Grafana Tempo |

## Frontend

- Next.js 14 App Router, TS strict, Tailwind + shadcn/ui.
- RTL Arabic primary (`ar-MA`), French secondary (`fr-MA`), **no English
  in user UI**.
- Per-role navigation computed from `GET /v1/me` (never trust the UI alone).
- Route-split per module; initial JS budget ≤ 180 KB gzipped (enforced in CI).
- Driver mode is the only role with offline support (IndexedDB + SW queue).

## Deploy

- **API + workers:** Fly.io, `cdg` primary + `ams` warm standby.
- **Web PWA:** Cloudflare Pages.
- **DB:** Neon (eu-central-1) with PITR + a read replica for analytics.
- **Secrets:** Fly secrets + Cloudflare secrets; never in the repo.
- **Data residency:** EU only. CNDP friendly.
