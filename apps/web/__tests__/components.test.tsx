import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Flag, ProbBar } from "@kickoff/ui";

describe("Flag", () => {
  it("renders a flag-icons element with an accessible label", () => {
    render(<Flag team={{ flag_code: "br", name: "Brazil" }} />);
    const el = screen.getByRole("img", { name: "Flag of Brazil" });
    expect(el.className).toContain("fi-br");
  });

  it("renders GB subdivision codes", () => {
    render(<Flag team={{ flag_code: "gb-eng", name: "England" }} />);
    expect(screen.getByRole("img", { name: "Flag of England" }).className).toContain(
      "fi-gb-eng",
    );
  });

  it("falls back to a labeled monogram when no licensed flag exists", () => {
    render(<Flag team={{ flag_code: null, name: "Czechoslovakia" }} />);
    const el = screen.getByRole("img", { name: /Czechoslovakia \(no flag available\)/ });
    expect(el.textContent).toBe("C");
    expect(el.className).not.toContain("fi-");
  });
});

describe("ProbBar", () => {
  it("exposes a screen-reader summary of all three probabilities", () => {
    render(
      <ProbBar
        probs={{ home: 0.5, draw: 0.2, away: 0.3 }}
        homeName="Norway"
        awayName="England"
      />,
    );
    expect(
      screen.getByRole("img", {
        name: "Norway win 50.0%, draw 20.0%, England win 30.0%",
      }),
    ).toBeInTheDocument();
  });

  it("segment widths match probabilities", () => {
    const { container } = render(
      <ProbBar probs={{ home: 0.25, draw: 0.25, away: 0.5 }} />,
    );
    const segs = container.querySelectorAll("[role='img'] > div");
    // jsdom normalizes "25.0%" -> "25%"
    expect(parseFloat((segs[0] as HTMLElement).style.width)).toBe(25);
    expect(parseFloat((segs[2] as HTMLElement).style.width)).toBe(50);
  });
});
