import { describe, expect, it } from "vitest";
import { biggestGaps, comparePortfolios } from "../lib/compare";
import type { GitHubPortfolioAnalysis, PortfolioScoreDimensionResult } from "../lib/types";

function dimension(key: string, score: number, rules: Array<[string, number, number, number]>): PortfolioScoreDimensionResult {
  return {
    key,
    label: key,
    points_earned: score,
    points_possible: 100,
    score,
    rules: rules.map(([ruleKey, weight, detected, analyzed]) => ({ key: ruleKey, label: ruleKey, weight, detected_repository_count: detected, analyzed_repository_count: analyzed })),
  };
}

function analysis(overall: number | null, dimensions: PortfolioScoreDimensionResult[]): GitHubPortfolioAnalysis {
  return { score: { version: "v1", is_available: overall !== null, overall_score: overall, scored_repository_count: 4, dimensions, is_partial: false, limitations: [] } } as unknown as GitHubPortfolioAnalysis;
}

const docs = (score: number, detected: number) => dimension("documentation_consistency", score, [["readme_usage", 9, detected, 4]]);
const tests = (score: number, detected: number) => dimension("testing_automation_adoption", score, [["ci_workflow", 12, detected, 4], ["tests_structure", 18, 0, 4]]);

describe("comparePortfolios", () => {
  it("finds the leader, the gap and the leader of every dimension", () => {
    const result = comparePortfolios(analysis(70, [docs(80, 4), tests(40, 1)]), analysis(55, [docs(60, 2), tests(40, 1)]));

    expect(result).toMatchObject({ scoreA: 70, scoreB: 55, leader: "a", gap: 15 });
    expect(result.dimensions.map((item) => [item.key, item.leader])).toEqual([
      ["documentation_consistency", "a"],
      ["testing_automation_adoption", "tie"],
    ]);
  });

  it("orders dimensions the way the result page does and keeps unknown ones last", () => {
    const hygiene = dimension("repository_hygiene_consistency", 50, []);
    const maintenance = dimension("maintenance_visibility", 50, []);
    const extra = dimension("zzz_new", 10, []);
    const result = comparePortfolios(analysis(10, [extra, maintenance, hygiene, tests(1, 0), docs(1, 0)]), analysis(10, []));

    expect(result.dimensions.map((item) => item.key)).toEqual(["documentation_consistency", "testing_automation_adoption", "repository_hygiene_consistency", "maintenance_visibility", "zzz_new"]);
  });

  it("compares rules by the share of analyzed repositories, not by raw counts", () => {
    const small = analysis(50, [dimension("documentation_consistency", 50, [["readme_usage", 9, 2, 2]])]);
    const large = analysis(50, [dimension("documentation_consistency", 50, [["readme_usage", 9, 3, 6]])]);

    const [rule] = comparePortfolios(small, large).rules;

    expect(rule).toMatchObject({ shareA: 1, shareB: 0.5, leader: "a", detectedB: 3, analyzedB: 6 });
  });

  it("does not declare a leader when a score is unavailable", () => {
    const result = comparePortfolios(analysis(null, []), analysis(60, []));

    expect(result).toMatchObject({ scoreA: null, scoreB: 60, leader: "tie", gap: null });
  });

  it("handles a rule present on one side only", () => {
    const result = comparePortfolios(analysis(10, [docs(10, 1)]), analysis(10, [dimension("documentation_consistency", 10, [])]));

    expect(result.rules[0]).toMatchObject({ key: "readme_usage", shareB: null, leader: "tie", analyzedB: 0 });
  });
});

describe("biggestGaps", () => {
  it("lists where a side is behind, heaviest rule first, up to the limit", () => {
    const a = analysis(40, [docs(20, 0), tests(30, 0)]);
    const b = analysis(80, [docs(90, 4), tests(80, 4)]);
    const comparison = comparePortfolios(a, b);

    expect(biggestGaps(comparison, "a").map((rule) => rule.key)).toEqual(["ci_workflow", "readme_usage"]);
    expect(biggestGaps(comparison, "a", 1).map((rule) => rule.key)).toEqual(["ci_workflow"]);
    expect(biggestGaps(comparison, "b")).toEqual([]);
  });
});
