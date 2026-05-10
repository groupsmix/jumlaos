# JumlaOS Admin & User Guide (Mali Beta)

## Roles

- **Owner**: full access — debtors, invoices, payments, exports, settings, billing.
- **Accountant**: debtors, invoices, payments, exports. No settings/billing.
- **Driver**: read-only access to today's collection list. No financial mutations.

## Onboarding a new business

1. Owner signs up with their MA phone number; OTP delivered via WhatsApp.
2. Owner enters business name, ICE, address.
3. Default module flags: `mali=true`, `talab=false`, `makhzen=false`.
4. Owner invites accountant and drivers via phone number.

## Daily flow (Mali)

1. **Add debtor** → fill name, phone, ICE (optional), city, credit limit.
2. **Record credit sale** → debtor → "زيد دين" → amount + due date + note.
3. **Record payment** → debtor → "خلّص" → amount + method (cash/transfer/cheque).
4. **Generate invoice** → finalize and download bilingual PDF.
5. **Tax export** → end of period, download DGI CSV.

## Hidden modules

Talab and Makhzen are not yet available. The navigation hides them for businesses without the corresponding flag. Do not advertise their availability.

## Support

Email: `support@jumlaos.ma`. Incident response runbook in `docs/runbooks/`.
