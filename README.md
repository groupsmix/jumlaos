# JumlaOS — جملة OS

> The operating system for Moroccan wholesalers.
> Replaces the paper carnet, WhatsApp chaos, and Excel sheet.

> **Release status:** `v0.1.0-beta` — **JumlaOS Mali Private Beta**.
> Only the **Mali** module is shipped. **Talab** and **Makhzen** are gated behind per-business feature flags (`modules_enabled`) and are **disabled by default** until their respective launches. Do not market this build as a complete Mali + Talab + Makhzen suite.

JumlaOS is a modular SaaS built around three sub-brands that map to the real
burning pains of a Moroccan **jumala** (wholesaler):

| Module | Arabic | What it does | Launches |
|---|---|---|---|
| **Mali** | مالي | Credit/debt ledger, digital invoicing, payment tracking, DGI-ready exports | MVP — week 10 |
| **Talab** | طلب | Structured WhatsApp order intake, voice/image triage, delivery routing | month 4 |
| **Makhzen** | مخزن | Phone-barcode inventory, multi-warehouse, expiry alerts, demand forecast | month 6 |

The full product plan lives in [`docs/plan.md`](docs/plan.md). This repository
is the **build-ready technical implementation** of that plan.

---

## Repository layout

```
jumlaos/
├── apps/
│   ├── api/              # FastAPI modular monolith (Python 3.12, uv)
│   │   └── src/jumlaos/
│   │       ├── core/     # auth, tenancy, RBAC, audit, domain events
│   │       ├── mali/     # debtors, debt events, invoices, payments, tax
│   │       ├── talab/    # WhatsApp ingestion, orders, deliveries (stub)
│   │       ├── makhzen/  # products, stock, warehouses (stub)
│   │       ├── analytics/
│   │       ├── whatsapp/ # Meta Cloud API gateway
│   │       ├── billing/  # CMI + CashPlus
│   │       └── shared/   # money, phone, fuzzy, fixtures
│   └── web/              # Next.js 14 App Router PWA, RTL Arabic-first
├── packages/
│   └── shared/           # zod schemas + TS types shared by web/api
├── docs/                 # product plan, architecture, ADRs, runbooks
├── infra/                # Fly.io, Cloudflare, Docker
├── scripts/              # one-off dev helpers
└── .github/workflows/    # CI: lint, typecheck, test, security, deploy
```

See [`docs/architecture.md`](docs/architecture.md) for a deeper tour.

---

## Quick start (local dev)

### Prerequisites

- **Python 3.12** (managed via `pyenv` or `uv`)
- **Node.js 20+** and **pnpm 9+** (`corepack enable` or `volta install pnpm`)
- **Docker** + `docker compose` (Postgres 16 + Redis 7)
- **uv** (`pipx install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Bootstrap

```bash
# 1. Install dependencies
pnpm install
(cd apps/api && uv sync --all-extras)

# 2. Start Postgres + Redis
docker compose -f infra/docker-compose.dev.yml up -d

# 3. Run database migrations + seed demo data
(cd apps/api && uv run alembic upgrade head)
(cd apps/api && uv run python -m jumlaos.scripts.seed_demo)

# 4. Start the API (http://localhost:8000)
(cd apps/api && uv run uvicorn jumlaos.main:app --reload)

# 5. Start the web PWA (http://localhost:3000)
pnpm --filter @jumlaos/web dev
```

### Running tests

```bash
pnpm -r test            # all workspaces
make test               # same, via root Makefile
make lint               # ruff + eslint + prettier
make typecheck          # mypy + tsc
make check              # lint + typecheck + test (what CI runs)
```

### Demo account

Seed data provisions one business with three users:

| Phone (E.164) | Role | Login OTP (dev only) |
|---|---|---|
| `+212600000001` | owner | `000000` |
| `+212600000002` | accountant | `000000` |
| `+212600000003` | driver | `000000` |

In `ENV=dev` the OTP is always `000000` — never in staging or prod.

---

## Tech stack (pinned)

| Layer | Choice |
|---|---|
| Backend | FastAPI 0.115, Pydantic v2, SQLAlchemy 2 async, Alembic |
| Background | Procrastinate (Postgres-backed queue) |
| DB | Postgres 16 (Neon in prod) |
| Cache / rate limit | Redis 7 (Upstash in prod) |
| Object storage | Cloudflare R2 (S3-compatible) |
| Frontend | Next.js 14 App Router + TS strict + Tailwind + shadcn/ui |
| State | TanStack Query + Zustand |
| i18n | next-intl, `ar-MA` (primary) + `fr-MA` |
| Barcode | `@zxing/browser` (phone camera) |
| PDF | WeasyPrint, Cairo/Amiri fonts (bilingual invoices) |
| Voice STT | OpenAI Whisper (`language=ar`) |
| Image OCR | Gemini 1.5 Flash vision (structured JSON output) |
| WhatsApp | Meta WhatsApp Cloud API |
| Auth | Phone OTP + JWT cookie, RBAC, Postgres RLS |
| Hosting | Fly.io (API + workers), Cloudflare Pages (web) |
| Observability | Sentry, Logtail, Grafana Cloud, PostHog EU |

**Intentionally not used:** GraphQL, Kafka, Kubernetes, Stripe, Lambda, MongoDB.

---

## Security & compliance

- **Data residency:** EU (Paris / Frankfurt). CNDP-friendly, low latency to MA.
- **Money:** stored as `BIGINT centimes`. Never floats.
- **Financial retention:** 10 years, immutable (DGI requirement).
- **Multi-tenant:** Postgres RLS + per-request `app.business_id` + authz tests on every endpoint.
- **Secrets:** never committed. `.env.example` documents expected variables.
- **Supply chain:** pinned lockfiles, Renovate weekly, `pip-audit` + `pnpm audit` in CI, `gitleaks` on every push.

See [`docs/security.md`](docs/security.md) for the full threat model.

---

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`AGENTS.md`](AGENTS.md).
In short:

- Follow the [module boundaries](docs/architecture.md#module-boundaries).
  `mali` may NOT import from `talab` directly; use `core.events`.
- Every endpoint needs a cross-tenant authz test.
- Never modify generated code (migrations, OpenAPI schemas) by hand.
- Commit conventionally: `feat(mali): add aging report`.

---

## License

Proprietary. © 2026 JumlaOS. All rights reserved.


## Release & versioning

- Current release: **v0.1.0-beta** — see [`CHANGELOG.md`](./CHANGELOG.md) and [`docs/release-notes/v0.1.0-beta.md`](./docs/release-notes/v0.1.0-beta.md).
- Pre-release security checklist: [`docs/security-checklist.md`](./docs/security-checklist.md).
- Deployment guide: [`docs/deployment.md`](./docs/deployment.md).
- Known limitations: [`docs/known-limitations.md`](./docs/known-limitations.md).
- Privacy: [`PRIVACY.md`](./PRIVACY.md) — Terms: [`TERMS.md`](./TERMS.md) — Security: [`SECURITY.md`](./SECURITY.md).
