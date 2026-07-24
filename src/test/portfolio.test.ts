import { describe, expect, it } from "vitest";
import { boundsAreFeasible, sumWeights } from "../lib/portfolio";

describe("portfolio controls", () => {
  it("totals allocation weights", () => {
    expect(sumWeights([{ weight: 0.2 }, { weight: 0.3 }, { weight: 0.5 }])).toBe(1);
  });

  it("detects infeasible concentration bounds", () => {
    expect(boundsAreFeasible(4, 0, 0.35)).toBe(true);
    expect(boundsAreFeasible(3, 0, 0.2)).toBe(false);
  });
});
