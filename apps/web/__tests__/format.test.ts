import { describe, expect, it } from "vitest";
import { fmtPct, fmtPP, fmtDate } from "@kickoff/shared";

describe("probability formatting", () => {
  it("formats probabilities as percentages", () => {
    expect(fmtPct(0.253)).toBe("25%");
    expect(fmtPct(0.253, 1)).toBe("25.3%");
    expect(fmtPct(1)).toBe("100%");
    expect(fmtPct(0)).toBe("0%");
  });

  it("formats percentage-point deltas with sign", () => {
    expect(fmtPP(3.2)).toBe("+3.2 pp");
    expect(fmtPP(-8.05)).toBe("-8.1 pp");
    expect(fmtPP(0)).toBe("+0.0 pp");
  });

  it("formats ISO dates for display", () => {
    expect(fmtDate("2026-07-09")).toBe("9 Jul 2026");
  });
});
