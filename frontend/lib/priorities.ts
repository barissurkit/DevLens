import type { PortfolioScoreDimensionResult } from "./types";

export interface Improvement {
  key: string;
  label: string;
  weight: number;
  missingRepositories: number;
  analyzedRepositories: number;
  /** Points the portfolio score would gain if every analyzed repository had the signal. */
  points: number;
}

/**
 * The rules that would raise the portfolio score the most. A rule contributes
 * weight × (repositories with the signal / analyzed repositories), so the gain from closing
 * the gap completely is weight × (missing / analyzed).
 */
export function topImprovements(dimensions: PortfolioScoreDimensionResult[], limit = 3): Improvement[] {
  return dimensions
    .flatMap((dimension) => dimension.rules)
    .filter((rule) => rule.analyzed_repository_count > 0 && rule.detected_repository_count < rule.analyzed_repository_count)
    .map((rule) => {
      const missing = rule.analyzed_repository_count - rule.detected_repository_count;
      return {
        key: rule.key,
        label: rule.label,
        weight: rule.weight,
        missingRepositories: missing,
        analyzedRepositories: rule.analyzed_repository_count,
        points: (rule.weight * missing) / rule.analyzed_repository_count,
      };
    })
    .sort((left, right) => right.points - left.points || right.weight - left.weight || left.label.localeCompare(right.label, "tr"))
    .slice(0, limit);
}
