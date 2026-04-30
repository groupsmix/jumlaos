# JumlaOS Audit — Remaining Fixes

Status as of 2026-04-30. Tracks findings from the end-to-end technical audit
(F01--F33) that are **not yet fully resolved**. Everything else is either
implemented on `main` (PRs #1--3), in PR #4 (`fix/audit-findings-p1-p2`),
or in the comprehensive fixes PR.

## Fully Implemented (no action needed)

| ID | Finding | Status |
|----|---------|--------|
| F01 | SQL injection via f-string `SET LOCAL` | Done (main) |
| F02 | Idempotency middleware wired + INSERT ON CONFLICT | Done (main) |
| F03 | Audit outbox pattern (same-session writes) | Done (main) |
| F04 | Migrate-check CI job | Done (PR #4) |
| F05 | Module boundary checker + CI | Done (PR #4) |
| F06 | Coverage omit fixes, re-baselined fail_under | Done (PR #4) |
| F07 | WhatsApp OTP delivery via Procrastinate | Done (main) |
| F08 | Per-phone OTP lockout with exponential backoff | Done (main) |
| F09 | CSRF middleware default-deny + SameSite=Strict | Done (main) |
| F10 | Redis-backed slowapi rate limits per endpoint | Done (main) |
| F11 | Tighten append-only triggers | Done (comprehensive PR) |
| F12 | Real HA: Fly config, min_machines, health checks | Done (main) |
| F13 | Worker tenant assertion via with_business_context | Done (main) |
| F14 | /readyz checks Redis + Procrastinate + R2 | Done (main) |
| F15 | Idempotency TOCTOU + scoped by (biz, user, key) | Done (main) |
| F17 | Disable /v1/docs in prod | Done (main) |
| F18 | OTP attempts increment loss fix | Done (comprehensive PR) |
| F19 | Refresh-token reuse detection (family_id) | Done (main) |
| F19-cleanup | OTP cleanup cron task | Done (PR #4) |
| F20 | OTP rate-limit moved to Redis via slowapi | Done (main) |
| F21 | _validate_prod_security gaps closed | Done (main) |
| F22 | Procrastinate driver documentation | Done (PR #4) |
| F23 | Deploy workflow (OIDC + Fly) | Done (PR #4) |
| F24 | Supply-chain hardening (trivy + SBOM) | Done (PR #4) |
| F25 | Body-size limit middleware | Done (main) |
| F26 | DLQ replay tooling | Done (PR #4) |
| F27 | Per-subscriber event offsets | Done (PR #4) |
| F28 | Nightly ledger drift check | Done (main) |
| F30 | Cross-tenant authz tests for Mali | Done (PR #4) |
| F31 | PWA service-worker scoping (NetworkOnly for /v1/*) | Done (PR #4) |
| F32 | Strict CSP headers in next.config.mjs | Done (PR #4) |
| F33 | Log-redaction policy (HMAC phone/IP hashing) | Done (PR #4) |

## Partially Implemented (needs follow-up)

| ID | Finding | What's done | What remains |
|----|---------|-------------|--------------|
| F29 | UUIDv7 + encrypt tax IDs | Crypto adapter exists; Debtor.ice_number encrypted on write/decrypt on read | Business model tax IDs (rc_number, if_number, cnss_number, dgi_taxpayer_id) need same encrypt/decrypt treatment; existing plaintext data needs a one-time migration script to encrypt in place; UUIDv7 `shared/ids.py` exists but is not yet wired into customer-facing external IDs |

## Not Started (low priority, tracked for future sprints)

None -- all 33 findings have at least partial implementation.

## Notes

- **F29 data migration**: Existing plaintext ice_number/tax ID values in the
  database must be encrypted via a one-time migration script. This should be
  run during a maintenance window since it touches every Business and Debtor
  row. The script should read each row, encrypt the field, and write it back
  in batches.

- **F29 UUIDv7 adoption**: `shared/ids.py` provides `new_uuid()` and
  `new_hex()` but no model or route uses them yet. Switching customer-facing
  IDs (debtor external ID, invoice public ID, etc.) to UUIDv7 requires:
  1. Adding a `public_id` column to relevant tables
  2. Populating it via migration
  3. Using it in API responses instead of the integer PK
  4. Updating frontend to use the new ID format

- **Branch protection**: F23 mentions requiring branch protection rules
  (require all CI jobs, linear history, code review, dismiss stale reviews,
  no force-push on main). These are GitHub repo settings, not code changes.
  Must be configured manually in the repository settings.
