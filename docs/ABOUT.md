# About JumlaOS

> **JumlaOS — جملة OS** is the operating system for Moroccan wholesalers
> (تجار الجملة). It collapses the everyday tools of a Casablanca / Fes /
> Tangier wholesaler — a notebook of debts (الكريدي), a WhatsApp inbox of
> orders (الطلبيات), and a stockroom (المخزون) — into one mobile-first,
> Arabic-first, offline-friendly app that any clerk on a 50€ Android can use.

This document explains **what** the project is, **for whom**, and **why it has
to exist**. The technical plan is in [`plan.md`](../plan.md). The roadmap of
what to build next is in [`RECOMMENDATIONS.md`](./RECOMMENDATIONS.md).

---

## 1. The user

A Moroccan wholesaler — a `tajer joumla` — typically:

- Owns a single warehouse in a souk or an industrial zone.
- Sells in cartons / sacks / kilos to **20–500 retail clients** on credit.
- Tracks debts in a paper notebook (**الكريدي**) or a WhatsApp chat history.
- Receives orders by WhatsApp text, voice notes, and photos of paper lists.
- Pays VAT every quarter and panics during DGI audits because nothing is
  reconciled.
- Speaks **Darija + French**, reads **Arabic + French**, and types in
  whichever script is faster — often a mix of both in a single sentence.
- Has a phone (Android, low-end, intermittent 4G) and **no laptop**.

The status quo: notebooks get lost, debts get forgotten, retailers play
wholesalers off each other, VAT filings are reconstructed from memory once a
quarter, and growing past ~100 clients becomes physically impossible.

## 2. The promise

A wholesaler who installs JumlaOS should be able to say, in one breath:

> _« أشكون اللي خاصو يخلصني هاد الأسبوع؟ »_
> _("Who owes me money this week?")_

…and get a sorted list of debtors with phone numbers, last payment, days
overdue, and a one-tap WhatsApp reminder in their dialect. Same speed as
flipping a notebook, but searchable, backed up, and exportable for the
accountant.

JumlaOS is **not** ERP. It does **not** try to be SAP, Odoo, or QuickBooks.
It is the smallest possible thing that replaces the notebook, the WhatsApp
inbox, and the stockroom whiteboard — and nothing else.

## 3. The three modules

| Module | Arabic | What it does | First version |
| --- | --- | --- | --- |
| **Mali** | مالي | Debts, payments, invoices, VAT export. The notebook, but searchable. | Week 10 (MVP) |
| **Talab** | طلب | WhatsApp order ingestion: text, voice notes (Whisper), photos of paper lists (Gemini Vision). | Week 14 |
| **Makhzen** | مخزن | Inventory + barcode scanning + low-stock alerts. | Week 18 |

A wholesaler can pay for **just Mali** (the entry tier), Mali + Talab, or the
full bundle. Modules share the same authentication, audit log, and reporting,
but each can ship and price independently.

## 4. The non-negotiables

These are the constraints that distinguish JumlaOS from a generic
"small-business app":

- **Arabic-first, RTL-first.** Not "Arabic supported." Default locale is
  `ar-MA`. French is secondary. Every screen reads right-to-left, every PDF
  prints right-to-aligned, every voice note is transcribed in Arabic.
- **Money is sacred.** All amounts are stored as `BIGINT` centimes, never
  floats. The debt ledger is **append-only**: corrections happen by voiding
  + re-issuing, never by mutation. Ten-year retention is mandatory because
  the DGI says so.
- **Multi-tenant by construction.** Postgres Row-Level Security + a
  per-request business context. A bug in a route handler must not be
  enough to leak data across businesses.
- **Phone is the only login.** No emails, no passwords. WhatsApp OTP because
  every wholesaler already has WhatsApp open all day.
- **Offline-tolerant PWA.** A wholesaler in a basement in the medina has 1
  bar of 3G. The app must keep working and reconcile later.
- **Modular monolith, never a microservice circus.** One repo, one deploy,
  one database. Module boundaries are enforced by **import rules + CI**, not
  by network calls.
- **EU data residency.** Postgres, R2, Redis, PostHog — all in EU regions.
  This is a hard requirement for any future French/Belgian customers and a
  nice-to-have for DGI compliance.
- **No GraphQL. No Kafka. No Kubernetes. No Stripe. No Lambda. No Mongo.**
  Every veto is intentional. We use REST + a single Postgres + Procrastinate
  + Fly.io machines + CMI/Cashplus + Cloudflare R2.

## 5. Why this is "better than 1% of the world"

Most Moroccan SaaS attempts at this market are either:

1. Generic clones of Western SMB tools, translated badly, that completely
   miss Darija, RTL, the DGI export format, and the WhatsApp-first behavior;
   **or**
2. Excel macros wrapped in a WhatsApp bot, with no real data model, no audit
   trail, no multi-tenancy, and no path to scale past 50 customers.

JumlaOS aims to be the first one that is **simultaneously**:

- Built like a serious software product (typed, tested, RLS, append-only
  ledgers, 10-year retention, observability from day one).
- Built **for** the wholesaler, not for an imagined "global SMB" — Darija
  voice notes, ICE/RC/IF/CNSS fields, CMI + Cashplus payments, MAD-only
  pricing, DGI CSV export.
- Priced for the Moroccan market (target: ~150 MAD / month for the entry
  tier — less than a single bad-debt write-off).

## 6. What this project is _not_

To keep scope honest, JumlaOS will explicitly **not**:

- Become a marketplace or B2B catalog. We help one wholesaler manage
  _their_ business; we do not match buyers and sellers.
- Become an accounting suite. We export to the accountant's tool. The
  accountant keeps their job.
- Become an ERP. No HR, no payroll, no manufacturing.
- Replace WhatsApp. We integrate with the WhatsApp Business API; we do not
  ask wholesalers or retailers to install another chat app.
- Replace cash. Cash will remain ~70% of payments for years. We just record
  it accurately.

## 7. Origin

This codebase was bootstrapped from a single instruction:

> _"start work on this project — make this project ready to launch and
> better than 1% of the world. no question, be fully autonomous."_

The architecture, module split, data model, and roadmap come from
[`plan.md`](../plan.md), which was the input alongside that instruction.
The first 10 weeks of execution target the Mali module: the notebook, but
better. Everything else builds on top of that foundation.
