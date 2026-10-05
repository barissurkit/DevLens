import { cleanup, render, screen, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { ScoringGuide } from "../components/scoring-guide";
import { isStrength } from "../components/score-methodology";
import { SCORE_MODERATE_MIN, SCORE_STRONG_MIN, scoreTone } from "../lib/presentation";
import { dimensionPoints, SCORE_BANDS, SCORING_GUIDE } from "../lib/scoring-guide";

afterEach(cleanup);

/** A recorded analysis scored by the backend (scoring v3): the source of truth the guide has to agree with. */
const recorded = JSON.parse(readFileSync(resolve(__dirname, "../e2e/fixtures/portfolio.json"), "utf-8")).analysis.score as {
  version: string;
  dimensions: Array<{ key: string; points_possible: number; rules: Array<{ key: string; weight: number }> }>;
};

describe("scoring guide data", () => {
  it("lists exactly the dimensions, rules and weights the backend scores with", () => {
    expect(recorded.version).toBe("v3");
    const guide = SCORING_GUIDE.map((dimension) => ({
      key: dimension.key,
      points: dimensionPoints(dimension),
      rules: dimension.rules.map((rule) => [rule.key, rule.weight]),
    }));
    const backend = recorded.dimensions.map((dimension) => ({
      key: dimension.key,
      points: dimension.points_possible,
      rules: dimension.rules.map((rule) => [rule.key, rule.weight]),
    }));

    expect(guide).toEqual(backend);
    expect(guide.reduce((sum, dimension) => sum + dimension.points, 0)).toBe(100);
  });

  it("takes the band limits from the thresholds the result screen colours the score with", () => {
    expect(SCORE_BANDS.map((band) => band.range)).toEqual([`${SCORE_STRONG_MIN}–100`, `${SCORE_MODERATE_MIN}–${SCORE_STRONG_MIN - 1}`, `0–${SCORE_MODERATE_MIN - 1}`]);
    expect([100, SCORE_STRONG_MIN, SCORE_STRONG_MIN - 1, SCORE_MODERATE_MIN, SCORE_MODERATE_MIN - 1, 0].map((score) => scoreTone(score).label)).toEqual(["Güçlü", "Güçlü", "Gelişebilir", "Gelişebilir", "Zayıf", "Zayıf"]);
  });
});

describe("ScoringGuide", () => {
  it("is one page with a single h1 and a section for each part of the policy", () => {
    render(<ScoringGuide />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Puanlama nasıl çalışır?");
    for (const name of ["100 puan dört boyuta bölünür", "Bir kural puanı nasıl kazandırır?", "Güçlü yön mü, gelişim alanı mı?", "Bütün kurallar", "Skor aralıkları", "Bilmen gerekenler"]) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
  });

  it("shows the formula and a worked example whose arithmetic is right", () => {
    render(<ScoringGuide />);

    expect(screen.getByText(/kural puanı = ağırlık × \(kanıtı olan repository ÷ analiz edilen repository\)/)).toBeInTheDocument();
    // 7 × 2/8 = 1.75, written with the Turkish decimal comma.
    expect(screen.getByText(/7 × 2\/8 =/).textContent).toContain("1,75 puan");
  });

  it("has a table row for every rule, with its weight", () => {
    render(<ScoringGuide />);

    const tables = screen.getAllByRole("table");
    expect(tables).toHaveLength(SCORING_GUIDE.length);
    SCORING_GUIDE.forEach((dimension, index) => {
      const rows = within(tables[index]).getAllByRole("row").slice(1);
      expect(rows).toHaveLength(dimension.rules.length);
      dimension.rules.forEach((rule, ruleIndex) => {
        expect(within(rows[ruleIndex]).getByRole("rowheader")).toHaveTextContent(rule.label);
        expect(within(rows[ruleIndex]).getAllByRole("cell")[1]).toHaveTextContent(String(rule.weight));
      });
    });
  });

  it("explains the three bands and the limits", () => {
    render(<ScoringGuide />);

    for (const band of SCORE_BANDS) expect(screen.getByText(band.range)).toBeInTheDocument();
    expect(screen.getByText(/en az iki repository/)).toBeInTheDocument();
    expect(screen.getByText(/Fork edilmiş ve arşivlenmiş/)).toBeInTheDocument();
  });
});

describe("isStrength", () => {
  const rule = (detected: number, analyzed: number) => ({ key: "k", label: "K", weight: 5, detected_repository_count: detected, analyzed_repository_count: analyzed });

  it("is true from half coverage up, like the backend policy", () => {
    expect(isStrength(rule(3, 6))).toBe(true);
    expect(isStrength(rule(4, 8))).toBe(true);
    expect(isStrength(rule(2, 6))).toBe(false);
    expect(isStrength(rule(0, 5))).toBe(false);
    expect(isStrength(rule(0, 0))).toBe(false);
  });
});
