# JumlaOS — Privacy Policy (Beta)

> Effective date: 2026-05-10.
> Operator: GroupsMix SARL (placeholder — replace with the registered legal entity before public launch).

## Data we process

- Account data: phone number, name, role, business membership.
- Business data: business name, ICE, address, debtors, invoices, payments, attached photos/PDFs.
- Operational metadata: login timestamps, IP address, device fingerprint (hashed), request logs.
- Communications metadata: WhatsApp message ids, delivery status (no content beyond what the user submits).

## Where data lives

- Primary database: Neon Postgres in EU (Paris / Frankfurt).
- Object storage: Cloudflare R2 in EU.
- Logs: Logtail EU region.
- Error tracking: Sentry EU region.
- Product analytics: PostHog EU region.

All processors are EU-resident and contractually bound to GDPR-equivalent terms. JumlaOS does not transfer personal data outside the EU.

## Retention

- Financial records: 10 years (DGI requirement).
- Auth logs: 12 months.
- Operational logs: 30 days.
- Backups: 35 days rolling PITR + 12 months monthly snapshots.

## Your rights (CNDP / GDPR)

- Access — request a JSON export of your account data.
- Rectification — edit profile, request correction of business data.
- Erasure — request account deletion; financial records are preserved per DGI law for the legal retention period and then purged.
- Portability — download your debtors, invoices, and payments as CSV.
- Objection / restriction — contact us at `privacy@jumlaos.ma`.

## Cookies

JumlaOS uses one strictly-necessary `Secure HttpOnly` session cookie. No third-party advertising cookies are set.

## Contact

`privacy@jumlaos.ma` — JumlaOS Data Protection Officer.
