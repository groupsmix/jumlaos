/**
 * Money helpers — mirror of jumlaos.shared.money on the backend.
 *
 * Everything is BIGINT centimes (1 MAD = 100 centimes). Floats are forbidden.
 * Conversion to Number for display only happens at the rendering edge.
 */

const CENTIMES_PER_DH = 100n;

export class MoneyError extends Error {}

/** Convert centimes (integer) to a fixed-2 dirhams string. Lossless. */
export function centimesToDhString(centimes: number | bigint): string {
  const c = typeof centimes === "bigint" ? centimes : BigInt(centimes);
  if (c < 0n) throw new MoneyError("centimes_negative");
  const dh = c / CENTIMES_PER_DH;
  const cc = (c % CENTIMES_PER_DH).toString().padStart(2, "0");
  return `${dh}.${cc}`;
}

/** Parse a string like "12.34" into centimes (BIGINT-safe number). */
export function dhToCentimes(input: string | number): number {
  const raw = typeof input === "number" ? input.toString() : input.trim();
  if (!/^\d+(\.\d{1,4})?$/.test(raw)) throw new MoneyError("invalid_money_string");
  const [intPart, fracPart = ""] = raw.split(".");
  const padded = (fracPart + "00").slice(0, 2);
  const rounded =
    fracPart.length > 2 && Number(fracPart[2]) >= 5
      ? Number(padded) + 1
      : Number(padded);
  const intC = Number(intPart) * 100 + rounded;
  if (!Number.isSafeInteger(intC)) throw new MoneyError("amount_overflow");
  return intC;
}

/** Format centimes for display in the chosen locale. */
export function formatMad(centimes: number | bigint, locale: "ar-MA" | "fr-MA" = "ar-MA"): string {
  const dh = centimesToDhString(centimes);
  if (locale === "ar-MA") {
    return `${dh.replace(".", ",")} د.م.`;
  }
  return `${dh} MAD`;
}

/**
 * Apply a VAT rate (in basis points, e.g. 2000 = 20%) to a subtotal.
 * Returns [vatCentimes, totalCentimes]. Half-up rounding.
 */
export function applyVat(
  subtotalCentimes: number,
  vatRateBps: number,
): [number, number] {
  if (subtotalCentimes < 0) throw new MoneyError("subtotal_negative");
  if (vatRateBps < 0 || vatRateBps > 10_000) throw new MoneyError("vat_out_of_range");
  const raw = (subtotalCentimes * vatRateBps) / 10_000;
  const vat = Math.round(raw);
  return [vat, subtotalCentimes + vat];
}
