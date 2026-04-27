/** Moroccan phone helpers — mirror of jumlaos.shared.phone. */

export class PhoneError extends Error {}

/** Normalize a Moroccan phone number to E.164 (`+212XXXXXXXXX`). */
export function normalizeMa(raw: string): string {
  const digits = raw.replace(/[\s().-]/g, "").replace(/^00/, "+");
  let body: string;
  if (digits.startsWith("+212")) body = digits.slice(4);
  else if (digits.startsWith("212")) body = digits.slice(3);
  else if (digits.startsWith("0")) body = digits.slice(1);
  else throw new PhoneError("unrecognized_phone_format");

  if (!/^\d{9}$/.test(body)) throw new PhoneError("phone_length_invalid");
  if (!/^[567]/.test(body)) throw new PhoneError("not_a_moroccan_mobile");
  return `+212${body}`;
}

export function isMoroccanMobile(e164: string): boolean {
  return /^\+212[67]\d{8}$/.test(e164);
}
