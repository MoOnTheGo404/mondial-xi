import { describe, expect, it } from "vitest";
import {
  decodeScenario,
  encodeScenario,
  scenarioToParams,
  type ScenarioMap,
} from "@/components/scenario-controls";
import { FORMATIONS } from "@/components/pitch";

describe("scenario URL persistence", () => {
  const scenario: ScenarioMap = {
    "norway/erling-haaland": { status: "unavailable", prob: 0 },
    "norway/martin-odegaard": { status: "doubtful", prob: 0.5 },
  };

  it("round-trips through the URL encoding", () => {
    const encoded = encodeScenario(scenario);
    const decoded = decodeScenario(encoded);
    expect(decoded["norway/erling-haaland"].status).toBe("unavailable");
    expect(decoded["norway/martin-odegaard"].status).toBe("doubtful");
    expect(decoded["norway/martin-odegaard"].prob).toBe(0.5);
  });

  it("ignores malformed segments instead of crashing", () => {
    expect(decodeScenario("garbage")).toEqual({});
    expect(decodeScenario("a/b:dNaN")).toEqual({});
    expect(decodeScenario(null)).toEqual({});
  });

  it("splits into API request params", () => {
    const { absences, doubtful } = scenarioToParams(scenario);
    expect(absences).toEqual(["norway/erling-haaland"]);
    expect(doubtful).toEqual([["norway/martin-odegaard", 0.5]]);
  });
});

describe("formations", () => {
  it("every formation has 10 outfield slots", () => {
    for (const [name, rows] of Object.entries(FORMATIONS)) {
      const total = rows.reduce((a, b) => a + b, 0);
      expect(total, `${name} outfield count`).toBe(10);
    }
  });
});
