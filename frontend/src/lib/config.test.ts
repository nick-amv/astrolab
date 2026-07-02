import { describe, expect, it } from "vitest";
import { DEFAULT_LOCALE, isSupportedLocale, SUPPORTED_LOCALES } from "./config";

describe("locale config", () => {
  it("ships ru and en (ru default)", () => {
    expect(SUPPORTED_LOCALES).toContain("ru");
    expect(SUPPORTED_LOCALES).toContain("en");
    expect(DEFAULT_LOCALE).toBe("ru");
  });

  it("validates supported locales", () => {
    expect(isSupportedLocale("ru")).toBe(true);
    expect(isSupportedLocale("en")).toBe(true);
    expect(isSupportedLocale("zz")).toBe(false);
  });
});
