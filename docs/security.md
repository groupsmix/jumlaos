# Security & compliance

## Principles

- **Least privilege, everywhere.** RLS + RBAC + scoped service accounts.
- **Defense in depth.** A bug in any single layer must not expose data.
- **Money is tamper-evident.** Append-only ledgers, DB constraints, nightly drift checks.

## Identity & access

| Concern | Control |
|---|---|
| Login | Phone + WhatsApp OTP (`+212…`), 6 digits, 10-min TTL |
| Lockout | 5 failed attempts → 15-min cooldown, logged |
| Session | JWT access token (15 min) + refresh cookie (30 days, HttpOnly, SameSite=Lax) |
| RBAC | roles: `owner`, `manager`, `staff`, `accountant`, `driver` |
| Tenant scoping | Postgres RLS + per-request `app.business_id` |
| Multi-user | One `user` may belong to N `businesses`; switching re-issues JWT |

Dev-only: `ENV=dev` short-circuits OTP to `000000`. A server-side assert
refuses to boot in staging/prod if this flag is true.

## Transport & data

- TLS 1.3 everywhere. HSTS preloaded. Certs via Cloudflare.
- Postgres connections require TLS (`sslmode=require` in prod).
- Database encryption at rest (Neon default).
- Object storage encryption at rest (R2 customer-managed keys).
- Signed URLs (5-min TTL) for any R2 download — no public buckets.

## Financial integrity

- `SUM(debt_balances) == SUM(non-voided debt_events)` nightly cron. Drift pages P0.
- `SUM(invoice_lines.line_subtotal_centimes) == invoice.subtotal_centimes` enforced by DB constraint + property tests.
- `SUM(stock_levels) == SUM(stock_movements)` nightly cron.
- Invoice numbers: gap-free, per-business, allocated via advisory lock.

## Threat model (summary)

See `docs/plan.md` §12 for the 30-item table. Highlights:

| # | Threat | Mitigation |
|---|---|---|
| S19 | Voice note PII leak | UUIDv7 R2 keys + signed URLs |
| S20 | LLM prompt injection from customer messages | Schema-bounded prompts, no user-controlled instructions, output-only schema |
| S21 | Invoice number gaps | DB constraint + advisory lock + reserved-number table |
| S22 | Driver marks "delivered" without delivering | Mandatory POD photo + GPS geofence |
| S23 | Stock count fraud | Audit log + owner notification on large moves |
| S25 | Webhook replay | `wa_message_id` dedup table, 30-day TTL |
| S26 | CMI callback spoofing | HMAC + IP allowlist + initiated-transaction match |
| S28 | Worker reads cross-tenant jobs | Tenant tag on every job, worker-side assertion |
| S30 | Migration leaks prod → staging | Separate Neon projects; CI rule blocks `prod` migrations from non-`main` branches |

## Secrets hygiene

- `.env` is gitignored. `.env.example` is the only env file committed.
- `gitleaks` runs on every push. A leak blocks the build AND pages the on-call.
- Access tokens rotate quarterly. Customer-visible keys (WhatsApp number,
  CMI merchant ID) rotate when an employee with access leaves.

## Compliance

- **CNDP (Morocco).** Declared data processing, EU residency, named DPO.
- **DGI (Morocco taxes).** 10-year invoice retention; gap-free numbering;
  monthly CSV export in the "Etat des factures" format.
- **RGPD (EU — customers in EU).** Data export + deletion endpoints;
  documented lawful basis per processing activity.

## Incident response

- Runbooks in `docs/runbooks/`.
- Sev-1 (money, data leak, auth bypass): page on-call within 5 min; publish
  public postmortem within 72h.
- Sev-2 (service down for >5 min): page on-call, internal postmortem within 7 days.
