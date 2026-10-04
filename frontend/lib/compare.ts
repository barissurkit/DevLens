import type { GitHubPortfolioAnalysis, PortfolioScoreDimensionResult } from "./types";

export type Side = "a" | "b" | "tie";

export interface DimensionComparison {
  key: string;
  label: string;
  a: PortfolioScoreDimensionResult | null;
  b: PortfolioScoreDimensionResult | null;
  /** Who is ahead on this dimension, by its 0-100 dimension score. */
  leader: Side;
}

export interface RuleComparison {
  key: string;
  label: string;
  weight: number;
  /** Share of analyzed repositories that have the signal, 0-1; null when nothing was analyzed. */
  shareA: number | null;
  shareB: number | null;
  detectedA: number;
  analyzedA: number;
  detectedB: number;
  analyzedB: number;
  leader: Side;
}

export interface PortfolioComparison {
  scoreA: number | null;
  scoreB: number | null;
  leader: Side;
  /** Absolute score difference, or null when either score is unavailable. */
  gap: number | null;
  dimensions: DimensionComparison[];
  rules: RuleComparison[];
}

const DIMENSION_ORDER = ["documentation_consistency", "testing_automation_adoption", "repository_hygiene_consistency"];

function leaderOf(a: number | null, b: number | null): Side {
  if (a === null || b === null) return "tie";
  if (a > b) return "a";
  if (b > a) return "b";
  return "tie";
}

function share(detected: number, analyzed: number): number | null {
  return analyzed > 0 ? detected / analyzed : null;
}

function byDimensionOrder(left: string, right: string): number {
  const leftIndex = DIMENSION_ORDER.indexOf(left);
  const rightIndex = DIMENSION_ORDER.indexOf(right);
  return (leftIndex === -1 ? DIMENSION_ORDER.length : leftIndex) - (rightIndex === -1 ? DIMENSION_ORDER.length : rightIndex);
}

/** Compares two portfolio analyses dimension by dimension and rule by rule. */
export function comparePortfolios(a: GitHubPortfolioAnalysis, b: GitHubPortfolioAnalysis): PortfolioComparison {
  const scoreA = a.score.is_available ? a.score.overall_score : null;
  const scoreB = b.score.is_available ? b.score.overall_score : null;

  const dimensionKeys = [...new Set([...a.score.dimensions, ...b.score.dimensions].map((dimension) => dimension.key))].sort(byDimensionOrder);
  const dimensions = dimensionKeys.map<DimensionComparison>((key) => {
    const left = a.score.dimensions.find((dimension) => dimension.key === key) ?? null;
    const right = b.score.dimensions.find((dimension) => dimension.key === key) ?? null;
    return { key, label: left?.label ?? right?.label ?? key, a: left, b: right, leader: leaderOf(left?.score ?? null, right?.score ?? null) };
  });

  const rules: RuleComparison[] = [];
  for (const dimension of dimensions) {
    const keys = [...new Set([...(dimension.a?.rules ?? []), ...(dimension.b?.rules ?? [])].map((rule) => rule.key))];
    for (const key of keys) {
      const left = dimension.a?.rules.find((rule) => rule.key === key);
      const right = dimension.b?.rules.find((rule) => rule.key === key);
      const shareA = left ? share(left.detected_repository_count, left.analyzed_repository_count) : null;
      const shareB = right ? share(right.detected_repository_count, right.analyzed_repository_count) : null;
      rules.push({
        key,
        label: left?.label ?? right?.label ?? key,
        weight: left?.weight ?? right?.weight ?? 0,
        shareA,
        shareB,
        detectedA: left?.detected_repository_count ?? 0,
        analyzedA: left?.analyzed_repository_count ?? 0,
        detectedB: right?.detected_repository_count ?? 0,
        analyzedB: right?.analyzed_repository_count ?? 0,
        leader: leaderOf(shareA, shareB),
      });
    }
  }

  return {
    scoreA,
    scoreB,
    leader: leaderOf(scoreA, scoreB),
    gap: scoreA !== null && scoreB !== null ? Math.abs(scoreA - scoreB) : null,
    dimensions,
    rules,
  };
}

/** The rules where `side` is clearly behind, largest weight first: what it would learn from the other portfolio. */
export function biggestGaps(comparison: PortfolioComparison, side: "a" | "b", limit = 3): RuleComparison[] {
  const other = side === "a" ? "b" : "a";
  return comparison.rules
    .filter((rule) => rule.leader === other)
    .sort((left, right) => right.weight - left.weight || left.label.localeCompare(right.label, "tr"))
    .slice(0, limit);
}
