# JumlaOS — Build-Ready Technical Plan for All 10 Jumala Wholesale Problems

**Audience:** AI code builder + product owner.
**Goal:** Build the operating system that replaces a Moroccan wholesaler's paper carnet, WhatsApp chaos, and Excel sheet — addressing **8 of the 10** pain points from your research as buildable SaaS, and being honest about the 2 that are not.
**Timebox:** **6 months** to a paid-customer-ready v1, with a usable MVP in **10 weeks**. If anyone tells you all 10 problems can be solved in 8 weeks, they're lying or building a demo.

This plan is brutally opinionated. Every decision is collapsed to a single choice. If you disagree, change it *before* the AI builder writes a line of code, not after.

---

## 0. The 60-second product spec

A Moroccan wholesaler (jumala) runs his entire business from a phone, a notebook, and a back room. He gets:
- ~30 inbound orders/day on WhatsApp (text, voice notes, screenshots, blurry photos of handwritten lists).
- He extends credit to 50–200 retailers and tracks debts on paper.
- He has no real-time stock visibility, no formal invoicing, no analytics, no demand forecast.
- 60–120 day average payment delays kill cash flow.

**JumlaOS does this, and only this:**

| # | Module | What it does | Maps to pain |
|---|---|---|---|
| **M1** | **Mali (مالي)** — Money | Credit/debt ledger, digital invoicing, payment tracking, DGI-ready exports | #2, #6, #9 |
| **M2** | **Talab (طلب)** — Orders | Structured WhatsApp order intake, voice/image triage, order confirmation, delivery routing | #1, #7 |
| **M3** | **Makhzen (مخزن)** — Stock & Insight | Phone-barcode inventory, multi-warehouse, low-stock alerts, demand forecast, perishable expiry | #5, #8, #10 |

Pain points **#3 (price transparency)** and **#4 (illegal market fees / corruption)** are **not in scope**. They are regulatory and political problems involving adversarial actors and government reform. A SaaS cannot fix them — claiming otherwise is dishonest. We'll discuss what we *can* contribute (anonymous price benchmarks, opt-in transparency) but not pretend it's the solution.

We launch with **M1 (Mali)** in week 10 because that's where the burning pain is and where money flows. **M2 (Talab)** ships at month 4. **M3 (Makhzen)** at month 6.

---

## 1. Reality check: which of the 10 are actually SaaS-solvable?

Before architecture, get the truth straight:

| # | Problem | SaaS-solvable? | Why / why not | What we ship |
|---|---|---|---|---|
| 1 | WhatsApp order chaos | **YES, fully** | Parser + structured intake replaces text/voice/screenshot mess | M2 Talab |
| 2 | Zero credit/debt tracking | **YES, fully** | Pure data problem. Already solved in plan v1 (DyaLi). | M1 Mali |
| 3 | No price transparency | **PARTIAL** | Requires adversarial cooperation from market operators. We can build *opt-in* anonymous price benchmarks across our customer base — but it won't fix the underlying broken market | Stretch goal: anonymous price index from our data, post-launch |
| 4 | Illegal fees / corruption in wholesale markets | **NO** | Adversarial actors, cash-based, off-the-books. We are not a judicial reform tool. | Out of scope. We can offer *audit trail tooling* for jumala who want to formalize, that's it. |
| 5 | Manual inventory | **YES, fully** | Phone-camera barcode scan + simple stock model | M3 Makhzen |
| 6 | No digital invoicing | **YES, fully** | Generate DGI-conformant invoices, archive 10 years | M1 Mali |
| 7 | Fragmented distribution / no end-to-end tracking | **PARTIAL** | We can solve *intra-jumala* tracking. Inter-jumala chains require the *next* jumala in the chain to also be on JumlaOS — network effect, takes years. | M2 Talab + roadmap |
| 8 | Perishable waste | **YES, partially** | Expiry tracking + smart sell-first logic + basic FEFO/FIFO. Doesn't fix truck congestion at markets — that's #4. | M3 Makhzen |
| 9 | Informal economy trap (no bank loans) | **YES, indirectly** | Once we have 6+ months of clean transaction data, we partner with a Moroccan bank/microfinance for receivable financing. Not built; *enabled*. | Year 2 partner play |
| 10 | No analytics / demand forecasting | **YES** | Once we have order + stock data, basic forecasting is straightforward | M3 Makhzen |

**Score: 7 fully solvable, 2 partially, 1 not at all.** Plan accordingly.

---

## 2. Hard product decisions (do not relitigate)

| Decision | Choice | Why |
|---|---|---|
| Brand | **JumlaOS** (English/Latin spelling); Arabic: **جملة OS**. Module sub-brands: Mali / Talab / Makhzen. | Easy to say across Darija/French/English. "OS" reads as serious tech. |
| Primary surface | **WhatsApp Cloud API** for ingest + alerts; **PWA** for management. | Same as DyaLi. The phone wins. |
| Native app | **No.** PWA only. | Avoid app store gatekeeping in v1; revisit at 5k+ paying users. |
| Languages | **Darija (Arabic script) primary, French secondary.** No English in user UI. | Same. |
| Currency | **MAD only.** Stored as `BIGINT centimes`. | Same. |
| Auth | **Phone + WhatsApp OTP**, multi-user supported from v1 (jumala wants to give read-only access to son/accountant). | Same as DyaLi but multi-user from day 1 — adding it later is painful. |
| Tenant model | One `business`, many `users`, role-based (owner / staff / accountant / driver). | Drivers need a reduced view (today's deliveries only). |
| Hosting region | **EU (Paris) on Fly + Neon.** | Same. |
| Payments collection (subscription) | **CMI + CashPlus manual.** | Same. |
| Modules toggleable | **YES.** Each module is feature-flagged + separately priced. | Customer can start with Mali (lowest barrier) and add modules. Critical for adoption. |
| Pricing | **Mali 99 MAD/mo · +Talab 199 MAD/mo bundle · +Makhzen 399 MAD/mo full bundle.** Free tier: Mali up to 20 active debtors. | Modular pricing matches modular product. |
| Multi-warehouse | **In v1 of M3, max 3 warehouses. Multi-region warehouse comes later.** | Most jumala have 1–2; few have 3+. |
| Barcode scanning | **Phone camera, in PWA, via `@zxing/browser`.** No dedicated scanner hardware in MVP. | Most jumala already have a smartphone; buying scanners is a barrier. |
| Voice note transcription | **YES, in M2.** Whisper API. ~MAD 0.06 per voice note. | This is the actual #1 unlock for "WhatsApp order chaos". Without voice, M2 is half-built. |
| Image OCR (handwritten orders) | **Cheap option in v1: Gemini 1.5 Flash vision.** Tesseract for printed Arabic is too weak. | Test on 100 real Moroccan handwritten order photos before committing. |
| Offline mode | **Limited:** PWA caches today's deliveries for drivers. Wholesaler-side requires online. | Drivers go to dead-zone neighborhoods. Wholesaler is at his shop on WiFi. |
| Tax compliance | **DGI-ready CSV + PDF invoice export.** Not direct DGI integration in v1. | DGI's e-invoicing API is still evolving (2026); don't lock to it yet. |
| Analytics depth | **Descriptive in M3 v1** (what happened). **Predictive in v2** (forecast). | Don't over-engineer ML before you have 90 days of data. |
| Data residency | **EU (Paris).** | CNDP-friendly, low latency to MA. |

---

## 3. Architecture (single picture, in words)

```
                                ┌──────────────────────────────────────────────┐
                                │ Wholesaler / Staff / Accountant / Driver     │
                                │  WhatsApp ───────┐    PWA (mobile)           │
                                └──────────────────┼─────────────┬─────────────┘
                                                   │             │
                               WhatsApp Cloud API ─┘             │ HTTPS
                                                                 │
                  ┌──────────────────────────────────────────────┴─────────────┐
                  │ Cloudflare (WAF, bot mgmt, DDoS, CDN, R2 object storage,   │
                  │ Turnstile for landing forms, Email Routing for ops)        │
                  └─────────────────────────────┬──────────────────────────────┘
                                                │
                     ┌──────────────────────────┴──────────────────────────────┐
                     │  API: FastAPI on Fly.io (cdg primary, ams hot standby)  │
                     │  ┌──────────────────────────────────────────────────┐   │
                     │  │ Modular Monolith — single repo, single deploy:    │   │
                     │  │   • core/        — auth, tenancy, audit, billing  │   │
                     │  │   • mali/        — debts, payments, invoices, tax │   │
                     │  │   • talab/       — orders, NLP, voice, OCR        │   │
                     │  │   • makhzen/     — products, stock, deliveries    │   │
                     │  │   • analytics/   — KPIs, forecasts, exports       │   │
                     │  │   • whatsapp/    — gateway, templates, parser     │   │
                     │  └──────────────────────────────────────────────────┘   │
                     └─────┬───────────┬──────────┬──────────┬─────────────────┘
                           │           │          │          │
                    Postgres 16     Redis 7   Procrastinate  R2 object store
                    (Neon EU,    (Upstash)   workers (Fly,   (receipts, voice,
                     read replica            separate proc)  images, PDFs,
                     + PITR)                                  CSV exports)

                     ┌─────────────────────────────────────────────────────────┐
                     │ External integrations                                    │
                     │  • Meta WhatsApp Cloud API (ingest + outbound templates) │
                     │  • OpenAI / Gemini (Whisper STT, Vision OCR, parser LLM) │
                     │  • CMI (subscription billing)                            │
                     │  • Sentry / Logtail / PostHog EU (observability)         │
                     │  • Resend (transactional email — receipts to accountant) │
                     └─────────────────────────────────────────────────────────┘

                     ┌─────────────────────────────────────────────────────────┐
                     │ Frontend: Next.js 14 PWA on Cloudflare Pages            │
                     │  • RTL Arabic primary, French secondary                  │
                     │  • Per-role nav: Owner / Staff / Accountant / Driver     │
                     │  • Barcode scan via getUserMedia + @zxing/browser        │
                     │  • Offline cache (driver mode only)                      │
                     └─────────────────────────────────────────────────────────┘
```

**Why a modular monolith, not microservices:**
- One deploy unit, one DB connection pool, one set of credentials, one log stream.
- Module boundaries enforced by **Python imports + an `archlint` rule that fails CI if `mali` imports from `talab` directly** — they go through `core` events.
- Splitting comes only when (a) one module's load dwarfs the others, or (b) the team grows to 10+ engineers. You are 1 engineer + AI. Stop pretending you're Netflix.

**Inter-module communication:**
- **Synchronous:** via well-defined Python interfaces in `core/services/`.
- **Asynchronous:** via a Postgres-backed event bus (Procrastinate jobs + a `domain_events` table) — e.g. `OrderConfirmed` → Mali creates draft invoice, Makhzen reserves stock.

---

## 4. Stack (final, pinned)

Same baseline as DyaLi plus additions for Talab and Makhzen.

| Layer | Choice | Notes |
|---|---|---|
| Backend | FastAPI 0.111+, Pydantic v2, SQLAlchemy 2 async, Alembic | Python 3.12, `uv` package mgr |
| Background | Procrastinate (Postgres queue) | one queue, multiple worker pools by tag |
| DB | Postgres 16 on Neon (eu-central-1) | with read replica for analytics |
| Cache / rate-limit | Upstash Redis (eu-west) | sliding window + sessions |
| Object storage | Cloudflare R2 | voice notes, images, PDFs, CSV |
| Frontend | Next.js 14 App Router + TS strict | static where possible, client where reactivity needed |
| Styling | Tailwind + shadcn/ui + custom RTL plugin | logical properties only |
| State | TanStack Query + Zustand | no Redux |
| Forms | react-hook-form + zod (codegen from FastAPI) | use `datamodel-code-generator` |
| i18n | next-intl, locales `ar-MA` (primary) and `fr-MA` | source-of-truth in Arabic |
| Barcode | `@zxing/browser` | EAN-13, EAN-8, Code128, QR |
| Charts | Recharts | only for M3 dashboards |
| PDF | WeasyPrint | Cairo/Amiri fonts for Arabic |
| Voice STT | OpenAI Whisper (ar) | ~$0.006/min, route via gateway with fallback to Gemini Audio |
| Image OCR | Gemini 1.5 Flash vision | structured JSON output |
| LLM parser fallback | Claude Haiku 3.5 / GPT-4o-mini, abstracted behind a `LLMRouter` | always with confidence + human confirm |
| WhatsApp | Meta Cloud API | 1 verified business number per environment |
| Payments | CMI prod + CashPlus manual | |
| Auth | Phone OTP + JWT cookie, RBAC | session 30 days, access token 15 min |
| Hosting | Fly.io for API + workers; Cloudflare Pages for web | |
| Observability | Sentry + Logtail + Grafana Cloud + PostHog EU | |
| CI/CD | GitHub Actions; Renovate weekly; gitleaks; pip-audit + npm audit | |
| Repo | Monorepo, pnpm workspaces: `apps/api` (Python), `apps/web` (Next), `packages/shared` (zod schemas, fixtures) | |

**No GraphQL. No Kafka. No Kubernetes. No Stripe. No Lambda. No Mongo.** Each veto is intentional. Don't let an AI builder reintroduce them.

---

## 5. Data model (Postgres, the source of truth)

All money: `BIGINT centimes`. All times: `TIMESTAMPTZ`. All tables: `id IDENTITY`, `created_at`, `updated_at`, `deleted_at` (soft delete; never hard delete financial data — Morocco 10-year retention).

### 5.1 Core (auth, tenancy, audit)

```
businesses
  id, owner_user_id, legal_name, display_name, phone_e164 UNIQUE,
  ice_number NULLABLE, rc_number NULLABLE, if_number NULLABLE,
  cnss_number NULLABLE, dgi_taxpayer_id NULLABLE,
  city, region, plan ENUM('mali','mali_talab','full'),
  trial_ends_at, status ENUM('active','suspended','terminated'),
  modules_enabled JSONB, default_warehouse_id NULLABLE,
  created_at, ...

users
  id, phone_e164 UNIQUE, display_name, locale, otp_lockout_until, last_login_at, ...

memberships              -- many-to-many user↔business with role
  id, user_id FK, business_id FK,
  role ENUM('owner','manager','staff','accountant','driver'),
  permissions JSONB,                 -- override role defaults
  status ENUM('active','revoked'),
  invited_by_user_id, accepted_at, ...
  UNIQUE (user_id, business_id)

audit_log                 -- everything that mutates state
  id, business_id, user_id, actor_kind, action, entity_type, entity_id,
  before JSONB, after JSONB, ip, user_agent, request_id, created_at
  INDEX (business_id, created_at DESC)
  INDEX (entity_type, entity_id)

domain_events             -- internal event bus, append-only
  id, business_id, kind TEXT, payload JSONB, version INT,
  emitted_at, processed_at NULLABLE,
  INDEX (business_id, kind, emitted_at)

otp_codes
subscriptions
webhook_dlq
```

### 5.2 Mali (money)

```
debtors                   -- retailers who buy on credit
  id, business_id FK, phone_e164, display_name, alias_normalized,
  city, address_text, credit_limit_centimes, payment_terms_days,
  risk_score INT (0-100), is_blocked, notes, ...
  UNIQUE (business_id, phone_e164)
  INDEX (business_id, alias_normalized)

debt_events               -- immutable ledger
  id, business_id FK, debtor_id FK,
  kind ENUM('debt','payment','adjustment','writeoff','refund'),
  amount_centimes BIGINT,                 -- positive=debt, negative=payment
  due_date, reference, source ENUM('whatsapp','web','order','import'),
  raw_message TEXT, related_invoice_id FK NULLABLE, related_order_id FK NULLABLE,
  voided BOOL, voided_reason, voided_at, voided_by_user_id,
  created_by_user_id, created_at
  INDEX (business_id, debtor_id, created_at DESC)
  PARTIAL (business_id, due_date) WHERE kind='debt' AND voided=FALSE

debt_balances             -- materialized projection
  business_id, debtor_id, total_outstanding_centimes,
  oldest_unpaid_due_date, days_past_due, last_payment_at
  PK (business_id, debtor_id)

invoices                  -- digital invoices, DGI-conformant
  id, business_id, debtor_id, number TEXT,         -- format: {YYYY}-{seq6}
  issued_at, due_at, status ENUM('draft','issued','paid','partial','void'),
  subtotal_centimes, vat_centimes, total_centimes,
  vat_rate_bps,                                    -- 2000 = 20%
  payment_terms_days, currency='MAD',
  pdf_url_signed,
  created_by_user_id, ...
  UNIQUE (business_id, number)

invoice_lines
  id, invoice_id FK, product_id FK NULLABLE, description, qty,
  unit_price_centimes, vat_rate_bps, line_subtotal_centimes, ...

payments                  -- recorded against an invoice or free
  id, business_id, debtor_id, invoice_id NULLABLE,
  method ENUM('cash','bank_transfer','cheque','cmi','cashplus','other'),
  amount_centimes, paid_at, reference, attachment_r2_key, ...

reminders                 -- WhatsApp reminders schedule
  id, business_id, debtor_id, debt_event_id NULLABLE, invoice_id NULLABLE,
  scheduled_at, sent_at, status, template_name, locale, attempt, error_code, wa_message_id

tax_periods               -- monthly closes for DGI export
  id, business_id, period_start, period_end, status ENUM('open','closed'),
  closed_at, closed_by_user_id, csv_export_r2_key
```

### 5.3 Talab (orders)

```
order_intakes             -- raw inbound (WhatsApp text/voice/image)
  id, business_id FK, source ENUM('whatsapp','web','phone'),
  from_phone_e164, raw_text, voice_r2_key, image_r2_key,
  transcript_text, transcript_confidence, ocr_text, ocr_confidence,
  parsed JSONB, parser_version, status ENUM('queued','parsed','confirmed','rejected'),
  created_at,
  INDEX (business_id, created_at DESC)

orders
  id, business_id FK, debtor_id FK NULLABLE,    -- nullable for cash/walk-in
  order_intake_id FK NULLABLE,
  number TEXT (UNIQUE per business),
  status ENUM('draft','confirmed','picked','out_for_delivery','delivered','cancelled','refused'),
  delivery_window_start, delivery_window_end,
  delivery_address_text, delivery_lat NULLABLE, delivery_lng NULLABLE,
  driver_user_id FK NULLABLE, vehicle_id NULLABLE,
  payment_method ENUM('cash_on_delivery','credit','prepaid','bank_transfer'),
  subtotal_centimes, total_centimes,
  notes,
  confirmed_at, delivered_at, ...

order_lines
  id, order_id FK, product_id FK NULLABLE,
  description, qty_requested, qty_picked, qty_delivered,
  unit_price_centimes, line_total_centimes, ...

deliveries
  id, order_id FK, driver_user_id, started_at, completed_at,
  proof_of_delivery_image_r2_key, signature_data NULLABLE,
  refusal_reason NULLABLE, gps_track_polyline NULLABLE
```

### 5.4 Makhzen (stock & insight)

```
warehouses
  id, business_id FK, name, address_text, lat, lng, is_default

products
  id, business_id FK, sku TEXT, barcode_ean TEXT NULLABLE,
  name_ar, name_fr, name_normalized,        -- search
  category, brand, supplier_id NULLABLE,
  unit ENUM('piece','kg','liter','box','dozen','bottle'),
  conversion_to_base_qty NUMERIC,
  default_purchase_price_centimes, default_sell_price_centimes,
  is_perishable BOOL, default_shelf_life_days INT,
  vat_rate_bps,
  image_r2_key,
  status ENUM('active','archived'),
  ...
  UNIQUE (business_id, sku)
  INDEX (business_id, barcode_ean)
  INDEX (business_id, name_normalized) USING GIN  (trigram)

stock_lots                -- one row per arrival (FEFO/FIFO support)
  id, business_id FK, product_id FK, warehouse_id FK,
  qty_remaining NUMERIC, unit_cost_centimes, supplier_id NULLABLE,
  received_at, expires_at NULLABLE, lot_number, ...
  INDEX (business_id, product_id, expires_at) WHERE qty_remaining > 0

stock_movements           -- ledger
  id, business_id, product_id, warehouse_id, lot_id NULLABLE,
  kind ENUM('receipt','sale','transfer_out','transfer_in','adjustment','writeoff','expiry'),
  qty NUMERIC,             -- signed
  unit_cost_centimes,
  related_order_id NULLABLE, related_invoice_id NULLABLE,
  reason TEXT, voided BOOL, ...
  INDEX (business_id, product_id, created_at DESC)

stock_levels              -- materialized projection per (warehouse, product)
  business_id, warehouse_id, product_id, qty_on_hand NUMERIC,
  qty_reserved NUMERIC, qty_available NUMERIC,
  last_movement_at,
  reorder_point NUMERIC, reorder_qty NUMERIC

suppliers
  id, business_id, name, phone_e164, contact_name, default_payment_terms_days, ...

forecasts                 -- M3 v2: rolling 30/60/90 day projections
  id, business_id, product_id, horizon_days, forecast_qty,
  computed_at, model_version, confidence_low, confidence_high
```

### 5.5 Analytics views (read replica)

Materialized views, refreshed nightly:
- `mv_top_debtors_30d`, `mv_aging`, `mv_collections_per_day`
- `mv_orders_per_day_per_city`, `mv_voice_intake_share`
- `mv_stock_turnover`, `mv_dead_stock_60d`, `mv_expiring_7d`, `mv_demand_history`

---

## 6. API design (REST, versioned, predictable)

Base: `https://api.jumlaos.ma/v1`. Same envelope, same auth (cookie + CSRF), same idempotency rules as DyaLi.

**Endpoints by module:**

### Core / Auth (10)
```
POST   /v1/auth/otp/request
POST   /v1/auth/otp/verify
POST   /v1/auth/logout
POST   /v1/auth/switch-business    -- user has memberships in N businesses
GET    /v1/me
PATCH  /v1/me
GET    /v1/businesses/current
PATCH  /v1/businesses/current
GET    /v1/memberships
POST   /v1/memberships/invite
PATCH  /v1/memberships/{id}        -- change role / revoke
```

### Mali (12)
```
GET/POST/PATCH/DELETE  /v1/debtors[/...]      (4 routes)
POST   /v1/debt-events                          -- log debt or payment
POST   /v1/debt-events/{id}/void
GET    /v1/dashboard/mali
GET    /v1/aging
POST   /v1/invoices                             -- draft from order or manual
GET    /v1/invoices                             -- list/filter
GET    /v1/invoices/{id}/pdf                    -- signed URL, 7-day TTL
POST   /v1/invoices/{id}/issue                  -- assigns number, locks
POST   /v1/invoices/{id}/payment
POST   /v1/tax-periods/{period}/close           -- generates DGI CSV
GET    /v1/tax-periods/{period}/export.csv
```

### Talab (10)
```
POST   /v1/webhook/whatsapp                     -- Meta inbound (signed)
GET    /v1/order-intakes                        -- triage queue
POST   /v1/order-intakes/{id}/confirm           -- promote to order
POST   /v1/order-intakes/{id}/reject
GET    /v1/orders
POST   /v1/orders                               -- manual create
PATCH  /v1/orders/{id}/status                   -- pick/deliver/refuse
POST   /v1/orders/{id}/assign-driver
GET    /v1/orders/{id}/route                    -- driver-only
POST   /v1/orders/{id}/proof-of-delivery        -- image + GPS + signature
```

### Makhzen (12)
```
GET/POST/PATCH/DELETE  /v1/products[/...]
POST   /v1/products/lookup-by-barcode           -- scanner endpoint
POST   /v1/stock-movements                      -- receipt/transfer/adjust
POST   /v1/stock-movements/bulk                 -- import CSV
GET    /v1/stock-levels                         -- ?warehouse=&low=true&expiring=7
GET    /v1/warehouses
POST   /v1/warehouses
GET    /v1/dashboard/makhzen
GET    /v1/forecasts                            -- v2
GET    /v1/exports/inventory.csv
```

### Billing & Ops (5)
```
POST   /v1/billing/cmi/checkout
POST   /v1/billing/cmi/callback
POST   /v1/billing/cashplus/claim
GET    /v1/health
GET    /v1/ready
```

**Total: ~50 endpoints, scoped tightly per module. No more.**

---

## 7. WhatsApp ingestion pipeline (Talab — the killer feature)

### 7.1 Pipeline overview

```
WhatsApp inbound  → webhook (signature verified)
                  → wa_inbound_messages row
                  → normalize (E.164 phone, MIME, language detect)
                  → classify intent (order? payment? debt? balance? help?)
                  → branch:
                      ├── TEXT  → rules-first parser → confidence?
                      │           ├── high → confirm card to wholesaler
                      │           └── low  → LLM parser → confirm card
                      ├── VOICE → Whisper STT (ar) → text path above
                      └── IMAGE → Gemini Vision OCR → structured JSON
                                  → validation → confirm card
                  → on confirm: write to orders + reserve stock + create draft invoice
```

### 7.2 Voice notes (the actual unlock)

Most "WhatsApp chaos" is voice notes. Strategy:
1. Download voice audio from Meta CDN.
2. **Whisper API with `language='ar'`** (Whisper handles Darija reasonably; not perfect but far better than nothing).
3. Apply post-processing rules: digit normalization (`خمسة آلاف` → `5000`), product name fuzzy match, name fuzzy match against debtors.
4. Confidence scoring per field (qty, product, name).
5. **If any field confidence < 0.75 → send a quick-reply card asking for confirmation**, never auto-commit.
6. Store the audio in R2 for 90 days for review/training.

### 7.3 Image OCR (handwritten orders)

Wholesalers receive handwritten lists photographed with bad lighting. Strategy:
1. Image → Gemini 1.5 Flash with a strict JSON schema prompt:
   ```
   Output: {
     "lines": [{"name_ar": "...", "qty": ..., "unit": "...", "price_per_unit_centimes": ...}],
     "low_confidence_fields": [...]
   }
   ```
2. Fuzzy match each `name_ar` against the wholesaler's product catalog.
3. **Always show the wholesaler the parsed table side-by-side with the original image** in the PWA triage queue. Never auto-commit.

### 7.4 Order grammar (text)

Tier 1 deterministic rules (regex + small grammar):
```
ORDER       :=  <name_token> ":" <line>+
LINE        :=  <product> [<qty>] [<unit>] [<price>]
PRODUCT     :=  fuzzy match against products (rapidfuzz, threshold 80)
QTY         :=  digits | Arabic words (واحد..عشرة)
```

Tier 2 LLM fallback under same constraints as DyaLi (schema-bounded, confirm-required).

### 7.5 Per-message hard rules

- **24h customer-service window** enforced at write time. Outbound free-form blocked outside; templates only.
- **Idempotency** by `wa_message_id`.
- **Replay safety:** every webhook is stored raw before any state mutation. A bad parser update can be rerun against history.
- **Quality monitor:** track Meta business quality rating; auto-throttle reminders if it drops below HIGH.

### 7.6 Confirmation UI

Every parsed order shows on the wholesaler's PWA triage screen:

```
┌────────────────────────────────────────────────┐
│  📞  +212 6 12 34 56 78  ·  Ahmed Tahiri        │
│  🎙️  Voice (45 sec)  ▶  Original transcript     │
│                                                 │
│  Parsed order:                                  │
│   • Coca-Cola 1.5L  ×  6 caisses                │
│   • Sidi Ali 0.5L  ×  10 caisses                │
│   • Pain de mie    ×  20 sachets                │
│                                                 │
│  Confidence: ⚠️ "Pain de mie" (low — confirm)  │
│                                                 │
│  [ Reject ]  [ Edit & Confirm ]  [ Confirm ]    │
└────────────────────────────────────────────────┘
```

The wholesaler taps Confirm. Order is created, stock reserved, debtor invoice drafted. He then taps "Send to driver" or "Send via WhatsApp for client confirmation" — never automatic shipping.

---

## 8. Inventory & perishable management (Makhzen)

### 8.1 Phone-camera barcode

- Open camera in PWA → `@zxing/browser` decodes EAN-13/EAN-8/Code128/QR locally (no upload).
- Lookup `POST /v1/products/lookup-by-barcode` → if product exists, show stock by warehouse; if not, prompt to create.
- Speed target: scan-to-screen < 1.5s on mid-range Android.

### 8.2 Stock model

- **Lot-based.** Each receipt creates a `stock_lots` row with cost + expiry. Sales pick lots **FEFO** (perishables) or **FIFO** (non-perishables).
- `stock_levels` is materialized for fast dashboard reads.
- Movements are append-only and signed (`+` for receipt, `-` for sale).

### 8.3 Perishable handling (problem #8, the part we can solve)

- `is_perishable` + `default_shelf_life_days` per product.
- Daily cron computes expiring-in-N-days reports.
- `mv_expiring_7d` drives a daily WhatsApp alert: *"⚠️ كاين 12 منتج غادي يخسر هاد الأسبوع. شوف القائمة [link]"*
- "Sell-first" badge in PWA on items expiring in <7 days. Optional auto-discount rule: -20% on items <5 days to expiry.
- **What we don't solve:** truck congestion at wholesale markets — that's #4 and outside SaaS.

### 8.4 Demand forecasting (M3 v2, after 90 days of data)

- Per-product time series of daily sales.
- **Start with naïve seasonal decomposition (statsmodels) + ETS**, not deep learning.
- Inject Moroccan calendar features: Ramadan, Eid, school holidays, Mawazine, Aid el Adha.
- Show a **range forecast** (P10/P50/P90), never a point estimate. Wholesalers understand ranges.
- Recompute weekly. Performance budget: <60s for 1000 products.

---

## 9. Digital invoicing & DGI tax compliance (Mali, problem #6)

### 9.1 Invoice generation

- Invoice numbering: `{YYYY}-{seq6}` per business, gap-free, monotonically increasing — Moroccan tax law requires this.
- VAT rates: 0%, 7%, 10%, 14%, 20% (current MA rates). Per-line VAT supported.
- PDF: WeasyPrint, A4, Arabic+French bilingual layout, ICE/RC/IF/CNSS in footer (auto-injected from `businesses` row).
- Once issued, **invoices are immutable.** Corrections via a credit note (`invoice.status='void'` + new credit-note invoice referencing original).

### 9.2 DGI export

- Monthly `tax_periods` close generates a CSV in DGI's "Etat des factures" format.
- The wholesaler downloads + uploads to the DGI portal (their portal API isn't ready for direct integration in 2026).
- Archive: each invoice PDF is stored in R2 with a 10-year retention policy + immutable bucket policy.

### 9.3 Auto-entrepreneur cap awareness

- Auto-entrepreneur status caps revenue at **500,000 MAD/year**. We track YTD revenue and warn at 80%/95%/100%.
- At 100%: prompt to upgrade legal status to SARL/SARL-AU; provide a checklist link, not legal advice.

### 9.4 What we do not promise

- We don't certify the wholesaler is tax-compliant. We make compliance easier. The wholesaler's accountant signs off.
- We do not file taxes for them. (Future product, but not v1.)

---

## 10. Frontend (PWA, Arabic-first, role-aware)

### 10.1 Per-role navigation

| Role | Sees |
|---|---|
| Owner | Everything. |
| Manager | Mali (full), Talab (full), Makhzen (full). No billing, no team mgmt. |
| Staff | Talab (intake + orders), Makhzen (stock counts). No money. |
| Accountant | Mali (read-only + invoice issue + tax export). Nothing else. |
| Driver | Today's deliveries only. Map. POD camera. Cash/credit recording. |

Role-based menus are computed server-side (`GET /v1/me` returns `permissions`) and enforced both in UI and API. **Never trust the UI to hide a button for security.**

### 10.2 Screens (count, not all listed)

- Mali: 6 screens (dashboard, debtors list, debtor detail, invoice editor, invoice list, tax close)
- Talab: 5 (intake queue, order detail, orders list, driver dispatch, driver app)
- Makhzen: 5 (stock dashboard, product list, product detail w/ scan, warehouse, expiry/low alerts)
- Core: 4 (login, settings, team, billing)
- **Total: ~20 screens.** Each must justify its existence.

### 10.3 Performance & accessibility

- LCP ≤ 2.0s on Moto G6 / 3G Fast. Enforced in CI.
- Initial JS budget: ≤ 180 KB gzipped (slightly higher than DyaLi for the extra modules; route-split per module).
- AA contrast min, AAA on monetary amounts.
- All interactive elements ≥ 44×44 CSS px.
- Driver mode: high-contrast, large fonts, works under sunlight.

### 10.4 Driver mobile UX (special)

- Big "Start route" button.
- Stop list with addresses → tap → opens Google Maps / Waze.
- Per-stop: "Delivered" / "Refused" / "Partial" buttons.
- Camera capture for proof of delivery.
- GPS track captured in the background, posted on completion.
- Works in airplane mode for one route (queues mutations, syncs on reconnect). **Driver is the only role with offline.**

---

## 11. Auth, RBAC, multi-tenancy

- Phone OTP unchanged from DyaLi.
- A `user` can belong to multiple `businesses` (rare but real — accountant serves 5 jumala). Switching business re-issues the JWT with new `business_id`.
- **Two layers of authz:**
  1. **Postgres RLS** with `SET LOCAL app.business_id = ...` per request.
  2. **Permission check in FastAPI dependency** based on role + module enabled.
- Authz tests are mandatory for every endpoint (cross-tenant fixture + cross-role fixture).

---

## 12. Security threat model (top 22 for this product)

Beyond DyaLi's threats, JumlaOS adds:

| # | Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| S1–S18 | (See DyaLi plan; all still apply) | — | — | — |
| S19 | **Voice note leaks PII** if R2 keys are guessable | High | High | UUIDv7 keys + signed URLs (5-min TTL) + private bucket |
| S20 | **OCR LLM exfiltrates customer data** if prompt templating is sloppy | Medium | High | Prompts are static + variables only; no user-controlled instructions; output-only schema; redact phone/CIN-style patterns before sending |
| S21 | **Invoice number gaps** trigger DGI audit | Medium | High | DB constraint + advisory lock during issue; never roll back issued numbers; reserved-number table with `holds` |
| S22 | **Driver app abuse** (driver marks "delivered" without delivering, pockets cash) | High | High | Mandatory POD photo + GPS within delivery polygon; cash declared per delivery; daily reconciliation reports; deviations flagged |
| S23 | **Stock count fraud** (staff scans a phantom 100-unit receipt) | Medium | High | All movements in audit log, owner notification on movements > X MAD; daily delta report; multi-person count required for adjustments > N |
| S24 | **Cross-business data leak via product catalog** (a popular product appears in many businesses; they may share an LLM cache) | Low | High | LLM calls never include other businesses' data; cache keyed strictly per business |
| S25 | **Webhook replay flooding** (attacker replays a captured WhatsApp webhook) | High | Medium | `wa_message_id` dedup table + 30-day TTL + rate limit per `from_phone` |
| S26 | **CMI callback spoofing** (fake "payment confirmed") | Medium | Severe | Verify HMAC signature + IP allowlist + match against initiated transaction id; never trust amount from callback alone |
| S27 | **Subdomain takeover** of a stale Cloudflare Pages preview | Medium | Medium | Tear down preview deployments on PR close; alarm on stale CNAMEs |
| S28 | **Procrastinate worker reads other tenants' jobs** (default behavior) | High | Severe | Tenant-scoped queue tags; `business_id` is part of the job payload; assertion in worker entrypoint |
| S29 | **Backups stored unencrypted in R2** | High | Severe | Server-side encryption with R2 customer-managed keys; restore drill quarterly |
| S30 | **AI builder leaks prod DB to staging** during a "migration"  | High | Catastrophic | Two separate Neon projects; DB URLs never share envs; CI rule blocks migrations against `prod` from any branch other than `main` |

**Money math + integrity (still the most important):**
- Daily cron: `SUM(stock_levels) == SUM(stock_movements)`, `SUM(debt_balances) == SUM(non-voided debt_events)`, `SUM(invoice_lines) == invoice.total`. Any drift = P0 page.
- Property tests on every monetary aggregator.

---

## 13. Morocco-specific edge cases (the AI builder will miss all of these)

1. **Multi-name disambiguation** ("محمد", "أحمد", "Mohamed" repeated dozens of times): require fuzzy match + last 4 digits of phone or alias.
2. **Ramadan and Eid:** reminder cadence shifts; demand forecasting must include Hijri-calendar features. Hard-code the next 5 Ramadans + Eids; don't compute from Hijri.
3. **Friday Jumu'ah pause** for outbound messaging.
4. **Sunday is the wholesale market day** in many regions. Don't pause Sunday.
5. **Address ambiguity outside Casa/Rabat** ("near the mosque, behind the souk"): allow address as free text + GPS pin from driver. Do not require structured address.
6. **Currency rounding** (rare 0.50 MAD overpayments): force-choose, no auto-credit.
7. **Voice notes in Darija mixed with French numbers** ("Ahmed 5 mille"): post-process Whisper transcript with both Arabic and French digit normalization.
8. **Phone formats:** 5 valid formats; one normalizer.
9. **Banking holidays + DGI deadline crunch:** invoice export must work the night before deadline; queue must be ready for spikes.
10. **"Carnet" handover** (jumala → son): "transfer ownership" flow with 7-day cooldown + email + WhatsApp confirmation.
11. **Cash-only payments confirmed via WhatsApp screenshot:** image upload → manual confirm. Don't promise OCR magic.
12. **Wholesale-market truck timings:** stock receipts often happen 03:00–06:00. Background workers must not throttle/sleep at those hours.
13. **MNO (mobile carrier) number recycling:** if a debtor's phone suddenly responds in a different style, flag for human review.
14. **VAT rate mix on a single invoice** is common. Per-line VAT, not per-invoice.
15. **DGI's "auto-entrepreneur" 500k cap** awareness everywhere we touch revenue.
16. **DGI portal accepts only Latin characters in some fields** — exporter must transliterate Arabic names to Latin (with override).
17. **CIH/Attijariwafa CMI subtle differences** in callback formats — test both.
18. **2026 Morocco-specific event:** drop-shipping bill in parliament. Stay agnostic on it; design so we can add KYC if law requires.

---

## 14. Performance, scale & cost

**Capacity targets:**
- v1 (10 weeks): 50 paying jumala, ~100 active debtors each, ~30 orders/day each, ~100 voice notes/day total.
- v1.5 (6 months): 500 paying, 100k orders/month, 5k voice notes/day.

**Bottlenecks expected, in order:**
1. **Voice note STT cost.** At 5k/day × $0.006/min × ~1 min avg = **~$30/day = ~MAD 9,000/mo just on Whisper**. Mitigation: cache by audio hash (rare) + cap per-business per-day with a fair-use alert.
2. **WhatsApp template approval queue** at Meta — slow human. Plan templates before launch.
3. **Postgres write-amp on `stock_movements`** at ~100k/day. Mitigate with partitioning by month at year-2.
4. **Procrastinate worker concurrency** — keep it stateless and horizontally scale.

**Cost model (monthly, EUR):**

| Item | 50 users | 500 users | 5000 users |
|---|---|---|---|
| Fly.io API + workers | €30 | €150 | €600 |
| Neon Postgres | €5 | €50 | €250 |
| Redis (Upstash) | €0 | €25 | €100 |
| R2 storage + bandwidth | €5 | €40 | €200 |
| Cloudflare Pro | €20 | €20 | €20 |
| WhatsApp Cloud API | €30 | €300 | €2,500 |
| Whisper STT | €30 | €300 | €3,000 |
| Gemini OCR | €5 | €50 | €500 |
| LLM parser fallback | €5 | €50 | €500 |
| Sentry + Logtail + PostHog + Grafana | €0 | €100 | €400 |
| Resend | €0 | €10 | €30 |
| Domain + misc | €5 | €5 | €5 |
| **Total infra** | **€135** | **€1,100** | **€8,100** |
| **Revenue (avg ARPU 199 MAD = €19, paid conv 35%)** | €330 | €3,300 | €33,000 |
| **Gross margin** | **59%** | **67%** | **75%** |

This is a profitable SaaS shape. The dangerous line items are Whisper + WhatsApp — both must be metered at the customer level and cost-allocated.

---

## 15. Observability & ops

- Metrics, logs, alerts as in DyaLi plus per-module:
  - `talab_intakes_total{type, status}`
  - `talab_voice_stt_duration_seconds`
  - `mali_invoices_issued_total{vat_rate}`
  - `makhzen_stock_movements_total{kind}`
  - `makhzen_expiring_units_total`
- 4 dashboards: Business Health · Reliability · Money Integrity · Cost-per-Tenant.
- Cost-per-tenant dashboard is critical: AI features mean costs scale per usage, not per seat.
- Backups: Neon PITR 7d + nightly logical dump to R2 + **monthly restore drill**.

---

## 16. CI/CD, testing — same shape as DyaLi but more

Coverage targets:
- 90% on any module touching money (Mali, parts of Makhzen).
- 80% on parser, voice pipeline, OCR pipeline.
- 60% elsewhere.
- E2E (Playwright) golden flows: 12 (login, debt log, payment, invoice issue, tax export, voice intake, image intake, order confirm, driver delivery, stock receipt, expiry alert, invoice PDF render).
- Load test (k6) before every major release: 100 concurrent webhooks + 50 concurrent invoice issues.
- Authz fuzzer: cross-tenant + cross-role on every endpoint, no exceptions.

---

## 17. Build order (6 months — phased, not parallel)

**Don't try to build all 3 modules in parallel. You will break under the load.**

### Phase 0 — Prep (week 0)
Same as DyaLi prep + Meta template designs for all 3 modules.

### Phase 1 — Mali MVP (weeks 1–10)
Same as the DyaLi plan, end-to-end. **Launch and bill 20 customers before Phase 2.** This is non-negotiable. Don't build M2 until you've collected MAD from at least 10 customers.

### Phase 2 — Talab MVP (weeks 11–18)
- W11–12: WhatsApp ingestion pipeline (text path), order_intakes triage UI.
- W13: Voice path (Whisper).
- W14: Image path (Gemini Vision).
- W15: Order entity + reservation logic, link to Mali invoices.
- W16: Driver app (PWA driver mode + POD).
- W17: End-to-end testing with 5 friendly jumala.
- W18: Public launch of Talab bundle.

### Phase 3 — Makhzen MVP (weeks 19–24)
- W19–20: Products + warehouses + barcode scan + stock movements.
- W21: Stock levels materialization, low-stock alerts.
- W22: Perishable expiry handling + alerts.
- W23: Basic descriptive analytics (30/60/90 day stock turn, dead stock).
- W24: Public launch of full bundle.

### Phase 4 — v2 features (months 7–12)
- Demand forecasting (real ML once 90+ days of data).
- Multi-warehouse transfers.
- Anonymous price benchmarks (opt-in cross-tenant) — partial answer to problem #3.
- Receivable financing partner (problem #9 partner play).

**What you do not build:**
- B2B marketplace (that's JumlaConnect, separate company).
- Affiliate platform (AfilMaghreb, separate).
- COD scoring (TasdiqPro, separate).
- Native mobile app.
- Multi-currency.
- Multi-country.

**Discipline matters more than code. Cut, don't add.**

---

## 18. What AI builders will get wrong (preempt them)

In addition to all the DyaLi footguns:

1. **Mix Mali/Talab/Makhzen logic in a single endpoint** "to save time". Reject any PR that violates module boundaries; enforce in CI with `archlint`.
2. **Auto-commit voice/image/text parses** without confirmation. NEVER. Confirmation card always.
3. **Generate invoice numbers with `MAX(seq)+1`** — race condition. Use Postgres advisory lock + a `invoice_number_sequences` table per business + per year.
4. **Use `FLOAT` for VAT** — 19.999999% rounding errors. Use BPS integers (`vat_rate_bps`).
5. **Skip lot tracking** in stock and use a single qty column. You cannot do FEFO without lots. Reject the shortcut.
6. **Hardcode VAT rate 20%** everywhere. Per-line VAT is mandatory.
7. **Forget the 24h customer-service window** for free-form WhatsApp. Add a runtime guard.
8. **Use Hijri calendar arithmetic** to compute Ramadan. Hard-code dates.
9. **Trust Whisper output verbatim** for amounts. Always validate + confirm.
10. **Send the entire product catalog to the LLM** for parsing each message. Send a top-K (50) shortlist via vector or trigram search.
11. **Run the LLM parser on every inbound message**. Rules-first; LLM only on rules-fail.
12. **Use `localStorage` for tokens or roles**.
13. **Build a "chat" inside the app**. WhatsApp is the chat.
14. **Build a "marketplace"** while we're at it. No.
15. **Use Stripe.** No.
16. **Add Kubernetes**. No.
17. **Mix "delete" with "void"** in the data model. Money is never deleted.
18. **Generate Alembic migrations with `--autogenerate` and not review them**.
19. **Skip property tests on money math** because "the unit tests pass".
20. **Render Arabic in PDFs without bidi reshaping**. Verify visually before merging.

Pin this list to the PR template. AI must confirm each before opening a PR.

---

## 19. Open questions you must answer before code

Block on these. Code without answers wastes a week.

1. **Module sequence:** start with Mali only (recommended), or Mali + Talab in parallel (risky)?
2. **Existing wholesalers willing to be design partners:** how many can you reach, in person, this month?
3. **DGI / accountant relationship:** do you already have an accountant who can validate the invoice format? If not, hire one (~MAD 3–5k for a one-time review).
4. **CMI sponsor bank:** Attijariwafa, CIH, BMCE, BMCI, Société Générale Maroc?
5. **WhatsApp business number:** clean, never-personal, ready to register?
6. **Brand:** "JumlaOS" / "Jumla" / something else? Claim domain + Meta business name early.
7. **Voice STT vendor preference:** OpenAI Whisper (~$0.006/min) or Gemini Audio? Pick one to default; we'll keep abstraction for fallback.
8. **Pricing tiers:** 99 / 199 / 399 MAD/mo (default) or different? Test on landing page first.
9. **Co-founder / ops human?** You cannot run support + build code + sell. Plan for it now.
10. **Funding runway:** 6 months self-funded, or are you raising? Affects buy-vs-build calls.

---

## 20. Things that will actually kill JumlaOS

Be honest about it. The 7 risks I'd bet money on:

1. **Scope creep across modules.** You ship a half-Mali, half-Talab, half-Makhzen and none works well. → Lock the phasing. Don't move to phase 2 without 10 paying Mali customers.
2. **WhatsApp account ban** (Meta is unforgiving). → Have a backup business number registered and idle. Throttle reminders. Monitor quality rating.
3. **AI cost overruns** (voice + LLM) on a free tier or on a stuck loop. → Per-tenant quotas + alerts at 80%. Daily cost report by tenant.
4. **DGI tax format change** mid-year. → Keep the export modular; build a "format adapter" layer.
5. **A wholesaler claims you cost him MAD X** because of a bug. → Audit log + integrity cron + 60-min undo + bug bounty. Already mitigated, but never zero risk.
6. **Founder burnout** running support during week 1–10. → Hire even part-time before launch.
7. **Cargo-cult "SaaS" pricing** that the actual jumala won't pay. → Validate willingness-to-pay with 30+ wholesalers BEFORE writing pricing in code. Letter-of-intent or pre-pay.

---

## 21. Definition of "v1 done"

You can't ship until all are true:

- [ ] A wholesaler can sign up via `jumlaos.ma` in <90s.
- [ ] He can record debts/payments/invoices via WhatsApp + web in Darija.
- [ ] He can ingest a WhatsApp voice note → confirm → order created → invoice drafted → stock reserved, end-to-end < 60s of human time.
- [ ] Driver app works in airplane mode for one route.
- [ ] DGI export passes review by 1 Moroccan accountant.
- [ ] Invoice PDF renders correctly in Arabic + French (visually verified).
- [ ] Cross-tenant authz pen-test: 0 violations.
- [ ] Money + stock integrity cron green for 14 days.
- [ ] CMI billing live with a real MAD 5 transaction.
- [ ] CNDP declaration filed.
- [ ] Restore drill done in last 14 days.
- [ ] Status page live.
- [ ] 10 paying customers (real money, not promo) using ≥2 modules each for 14 days.
- [ ] NPS ≥ 8 from those 10.

When all 14 are true: announce. Until then: closed beta.

---

## 22. What I need from you to start

Reply with answers (or "use default") for the 10 open questions in §19, plus:

- **Confirm:** Mali first (10 weeks), then Talab (8), then Makhzen (6). YES/NO?
- **Confirm:** problems #3 (price transparency) and #4 (illegal market fees) are *NOT* in scope as SaaS. YES/NO?
- **Confirm:** modular monolith, single repo, single deploy. YES/NO?
- **Confirm:** Arabic primary / French secondary / no English UI. YES/NO?

Once I have your answers (or "default everything"), we move to **Week 0 — accounts + Meta templates + DGI accountant review**, then **Week 1 — repo skeleton + auth + first deploy of Mali**.

---

*End of plan. 6 months, ~50 endpoints, ~20 frontend screens, ~30 DB tables, 1 backend, 1 frontend, 1 DB, 3 modules. Anything more is scope creep. Anything less is a demo, not a product.*
