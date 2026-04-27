# JumlaOS — Recommended Next Steps

> Status as of the initial bootstrap (commit on `main`):
> backend + Mali MVP + frontend skeleton are in, all CI green, **but**
> nothing is yet wired to a real database, real WhatsApp, or a real host.
> This file is the prioritized to-do list to take JumlaOS from
> "green CI on a laptop" to "production traffic in Casablanca."
>
> Each step lists **what is needed from you** (creds / decisions) and
> **what JumlaOS will do once that is provided**.

---

## Track A — Stand up real infrastructure (week 1–2)

### A1. Neon Postgres (EU)

**Need from you**

- Create a Neon project in **eu-central-1** (Frankfurt) or **eu-west-2**
  (Paris). Free tier is fine to start.
- Add a `DATABASE_URL` and `DATABASE_URL_REPLICA` (read replica branch) as
  a saved Devin secret.

**What JumlaOS will do**

- Run `alembic upgrade head` against Neon (the initial migration is
  already in `apps/api/alembic/versions/20260427_0001_init.py`).
- Apply RLS policies (`USING (business_id = current_setting('app.business_id')::bigint)`)
  to every per-tenant table.
- Add a Neon-specific `psql` health probe to `/v1/health`.
- Wire Procrastinate's job table on the same database.

### A2. Upstash Redis (EU)

**Need from you**

- Create an Upstash Redis database in **eu-west-1** (Ireland).
- Save `REDIS_URL` (rediss://… with TLS).

**What JumlaOS will do**

- Use Redis for rate-limiting (OTP, login, public webhook endpoints).
- Use Redis for hot-path caches (user → memberships, business config).
- Add a Redis ping to `/v1/health`.

### A3. Cloudflare R2 (object storage)

**Need from you**

- Create an R2 bucket `jumlaos-prod` (and `jumlaos-dev`).
- Generate a scoped API token (read+write on those two buckets).
- Save `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ACCOUNT_ID`,
  `R2_BUCKET_PROD`, `R2_BUCKET_DEV`.

**What JumlaOS will do**

- Store invoice PDFs (WeasyPrint output), CSV exports, payment-attachment
  uploads, and WhatsApp media downloads in R2.
- Sign short-lived (5-minute) URLs for browser downloads.
- Implement R2 lifecycle rules (90 days for transient WhatsApp media,
  10 years for invoices and audit exports).

---

## Track B — WhatsApp Business (week 2–3)

### B1. Meta WhatsApp Business API

**Need from you**

- A **Meta Business Account** (verified, ideally with the wholesaler's
  legal entity).
- A **WhatsApp Business Account (WABA)** with a registered display name
  and phone number (this number cannot also be used in the WhatsApp
  consumer or Business app).
- A **System User** with permission on the WABA, plus its long-lived
  access token.
- Save: `META_APP_ID`, `META_APP_SECRET`, `WABA_ID`, `WABA_PHONE_ID`,
  `META_SYSTEM_USER_TOKEN`, `WHATSAPP_VERIFY_TOKEN` (any random string
  you choose for the webhook handshake).

**What JumlaOS will do**

- Subscribe the webhook at `POST /v1/whatsapp/webhook` to messages,
  message_status, and template events.
- Submit and translate **payment-reminder** and **OTP** templates in
  Arabic + French to Meta for approval.
- Send templated reminders via Procrastinate task (`mali.send_reminder`).
- Persist undecodable webhook payloads to `webhook_dlq` for replay.

### B2. Voice + image parsing (for Talab)

**Need from you**

- An **OpenAI** API key (`OPENAI_API_KEY`) — used for Whisper STT on
  Arabic voice notes.
- A **Google Vertex AI** or Gemini API key (`GEMINI_API_KEY`) — used for
  vision OCR of paper-list photos.
- An **Anthropic** key (`ANTHROPIC_API_KEY`) and / or OpenAI key — used
  as the LLM-parser fallback for messy text orders (Claude Haiku 3.5 /
  GPT-4o-mini).

**What JumlaOS will do**

- Implement `talab.parse_voice` (Whisper → text → LLM → structured order).
- Implement `talab.parse_image` (Gemini Vision → structured order).
- Implement `talab.parse_text` (regex-first, LLM-fallback parser).
- Always require a human review step before an order becomes a debt.

---

## Track C — Hosting (week 3)

### C1. Fly.io (API + workers)

**Need from you**

- A Fly.io account; create an organization (e.g. `jumlaos`).
- A **Fly API token** scoped to that org. Save as `FLY_API_TOKEN` org
  secret.

**What JumlaOS will do**

- Generate `fly.toml` for two apps: `jumlaos-api` and `jumlaos-worker`,
  both deployed to **`cdg`** (primary) with hot standby in **`ams`**.
- Set autoscaling: 1–4 web machines, 1–2 worker machines.
- Wire health checks against `/v1/health` with a 30s timeout.
- Add a deploy GitHub Action that runs `fly deploy --remote-only` on
  every push to `main` after CI passes.

### C2. Cloudflare Pages (frontend PWA)

**Need from you**

- A Cloudflare account, an API token with Pages:Edit + Account:Read.
- The `groupsmix/jumlaos` repo connected to a new Pages project.
- DNS for the chosen domain (e.g. `app.jumlaos.ma`).

**What JumlaOS will do**

- Build command: `pnpm install --frozen-lockfile && pnpm --filter @jumlaos/web build`.
- Output dir: `apps/web/.next`.
- Set `NEXT_PUBLIC_API_BASE_URL=https://api.jumlaos.ma/v1` and the locale
  cookie name as Pages env vars.
- Add CORS allowlist on the API for the Pages preview + production domains.

### C3. Domains + email

**Need from you**

- Buy / point `jumlaos.ma` (and ideally `.com` defensively).
- Choose one of: Resend / Postmark for transactional email (low priority —
  WhatsApp is the primary channel; email is for accountant exports only).

**What JumlaOS will do**

- Configure Cloudflare DNS: `app.` → Pages, `api.` → Fly, `wa.` → Fly
  (separate pool for webhook ingress).
- Add SPF + DKIM if email is enabled.

---

## Track D — Background workers (week 3–4)

### D1. Procrastinate worker

**Need from you**

- Nothing new — uses the same Postgres as the API.

**What JumlaOS will do**

- Implement and ship these tasks:
  - `core.send_otp_whatsapp` — deliver OTP via WhatsApp template.
  - `core.send_otp_sms_fallback` — SMS fallback if WhatsApp delivery fails
    (needs a Moroccan SMS provider — see D2).
  - `mali.render_invoice_pdf` — WeasyPrint → R2.
  - `mali.send_reminder` — templated WhatsApp reminder.
  - `mali.recompute_balance` — projection refresh (already implemented
    inline; this is the async version triggered by `domain_events`).
  - `mali.export_tax_period_csv` — DGI-format CSV → R2.
- Add a Procrastinate dashboard mounted at `/admin/procrastinate` (owner
  role only).

### D2. SMS fallback (optional but recommended)

**Need from you**

- A Moroccan SMS gateway account (Maroc Telecom Business, Inwi Business,
  or a reseller like Twilio + Maroc Telecom shortcode). Save the
  credentials as `SMS_PROVIDER_*`.

**What JumlaOS will do**

- Add a `core.sms` adapter behind a feature flag.
- Use SMS for OTP only when WhatsApp delivery_status returns `failed` or
  `undeliverable` for >2 minutes.

---

## Track E — Talab MVP (week 12–14)

**Need from you**

- The credentials in **B1** and **B2**.
- A pilot wholesaler willing to forward a few hundred order messages.

**What JumlaOS will do**

- Implement `talab.orders` table + state machine
  (`received → parsed → confirmed → fulfilled → invoiced`).
- Build the WhatsApp ingest pipeline (webhook → media download → parser →
  draft order → human review).
- Build the order-review UI in the PWA (split view: original message on
  the right, parsed line items on the left, edit + confirm).
- Emit `order.fulfilled` domain events that Mali subscribes to in order
  to auto-create invoices.

---

## Track F — Makhzen MVP (week 16–18)

**Need from you**

- A list of the pilot wholesaler's top ~200 SKUs (CSV is fine — we'll
  build an importer).

**What JumlaOS will do**

- Implement `makhzen.products`, `makhzen.stock_movements` (append-only),
  `makhzen.stock_levels` (projection).
- Implement barcode scanning in the PWA via `@zxing/browser` (camera
  access already permitted in the security headers).
- Implement low-stock alerts as Procrastinate cron jobs.
- Wire Talab → Makhzen so confirmed orders deduct stock atomically.

---

## Track G — Compliance + observability (continuous)

### G1. DGI export hardening

- Already scaffolded in `mali.routes.tax_period_export_csv`. Before going
  live: have a Moroccan accountant validate the CSV columns against a
  recent quarterly filing, and pin the exact format with a snapshot test.

### G2. Observability

**Need from you**

- Sentry account (free tier). `SENTRY_DSN`.
- Logtail / BetterStack account. `LOGTAIL_TOKEN`.
- PostHog **EU** account. `POSTHOG_API_KEY`.

**What JumlaOS will do**

- Wire Sentry middleware in FastAPI + Sentry SDK in the Next.js app.
- Ship structured logs to Logtail with `business_id` + `request_id` on
  every line.
- Add PostHog opt-in product analytics with PII stripped.

### G3. Backups

**What JumlaOS will do (no creds needed)**

- Configure Neon point-in-time recovery (7 days on free, 30 on paid).
- Daily logical dump (`pg_dump`) → R2 with 90-day retention.
- Monthly restore drill via a GitHub Action that spins up an ephemeral
  Neon branch and runs `alembic upgrade head` + a smoke test.

---

## Track H — Billing + go-to-market (week 8–12)

### H1. CMI / Cashplus integration

**Need from you**

- A CMI merchant account (the dominant Moroccan card processor).
- A Cashplus business account (cash-deposit network used by SMBs without
  a card).
- Decide pricing tiers in MAD (suggested: 149 / 299 / 499 MAD/month).

**What JumlaOS will do**

- Implement `billing.subscriptions` reconciliation against CMI 3DS
  callbacks (CMI uses a hosted page; we never touch card numbers).
- Implement Cashplus voucher import (CSV polling).
- Add a self-serve plan-upgrade flow in the PWA.

### H2. Pilot

- Recruit 3–5 wholesalers (one per major souk: Casablanca derb omar,
  Fes batha, Tangier ziaten).
- White-glove onboarding for the first month: import their notebook
  manually into Mali, sit with them through one week of debt collection.
- Use the pilot to pin the WhatsApp template wording (Darija matters).

---

## Definition of "ready to launch"

The project is ready for paid customers when **all of these are true**:

- [ ] Tracks **A1–A3, B1, C1, C2, D1** are done — i.e. real DB, real
      WhatsApp, real hosts, real workers.
- [ ] Mali's full happy path (debtor → debt → reminder → payment → DGI
      CSV) is exercisable end-to-end on the deployed app.
- [ ] At least one wholesaler has used JumlaOS for **30 days** as their
      primary debt notebook without falling back to paper.
- [ ] Sentry + Logtail show < 0.1% error rate over the last 7 days on the
      Mali endpoints.
- [ ] DGI CSV export matches a real accountant's expected format,
      validated against a real filing.
- [ ] One full disaster-recovery drill has been performed (drop the
      Neon branch, restore from R2 backup, verify data parity).

Anything beyond that — Talab, Makhzen, multi-warehouse, marketplace —
is **growth**, not launch.
