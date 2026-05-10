# Known Limitations — v0.1.0-beta

- Talab (WhatsApp order intake) is not available; routes are stubs.
- Makhzen (inventory) is not available; routes are stubs.
- Analytics is limited to the basic Mali dashboard tiles.
- Offline / poor-network PWA behavior is best-effort.
- DGI export format is provisional pending final 2026 schema confirmation.
- The Procrastinate worker driver runs on the same Postgres as the API; isolate to its own role/schema before scaling above ~50 tenants.
- WeasyPrint PDF rendering is single-threaded; expect ~300 ms per invoice. Pre-warm fonts in production.
- Real CMI / CashPlus billing flows are not enabled by default; integration is feature-flagged off until provider credentials are validated in staging.
- Email transactional delivery requires Resend/Postmark domain verification before going live.
