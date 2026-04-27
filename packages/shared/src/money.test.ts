import { describe, expect, it } from "vitest";
import { applyVat, centimesToDhString, dhToCentimes, formatMad } from "./money";

describe("centimesToDhString", () => {
  it("formats whole dirhams", () => {
    expect(centimesToDhString(1000)).toBe("10.00");
  });
  it("formats fractional dirhams", () => {
    expect(centimesToDhString(1234)).toBe("12.34");
  });
});

describe("dhToCentimes", () => {
  it("parses whole numbers", () => {
    expect(dhToCentimes("10")).toBe(1000);
  });
  it("parses two decimals", () => {
    expect(dhToCentimes("12.34")).toBe(1234);
  });
});

describe("applyVat", () => {
  it("computes 20% VAT", () => {
    expect(applyVat(10_000, 2000)).toEqual([2_000, 12_000]);
  });
  it("rejects out-of-range bps", () => {
    expect(() => applyVat(100, -1)).toThrow();
    expect(() => applyVat(100, 10_001)).toThrow();
  });
});

describe("formatMad", () => {
  it("uses Arabic suffix", () => {
    expect(formatMad(1234, "ar-MA")).toContain("د.م.");
  });
  it("uses MAD suffix", () => {
    expect(formatMad(1234, "fr-MA")).toContain("MAD");
  });
});
