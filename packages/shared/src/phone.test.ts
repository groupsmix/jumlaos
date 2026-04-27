import { describe, expect, it } from "vitest";
import { isMoroccanMobile, normalizeMa, PhoneError } from "./phone";

describe("normalizeMa", () => {
  for (const raw of [
    "0612345678",
    "06 12 34 56 78",
    "+212612345678",
    "00212612345678",
    "212612345678",
  ]) {
    it(`normalizes ${raw}`, () => {
      expect(normalizeMa(raw)).toBe("+212612345678");
    });
  }
  it("rejects garbage", () => {
    expect(() => normalizeMa("abc")).toThrow(PhoneError);
  });
});

describe("isMoroccanMobile", () => {
  it("accepts mobile prefixes", () => {
    expect(isMoroccanMobile("+212612345678")).toBe(true);
    expect(isMoroccanMobile("+212712345678")).toBe(true);
  });
  it("rejects landlines", () => {
    expect(isMoroccanMobile("+212522222222")).toBe(false);
  });
});
