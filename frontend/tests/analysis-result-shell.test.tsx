import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AnalysisResultShell } from "../components/analysis-result-shell";
import type { GitHubPortfolioInterpretationResponse } from "../lib/types";

vi.mock("../components/auth-provider", () => ({ useAuth: () => ({ status: "authenticated", user: { github_login: "alice" } }) }));
vi.mock("../components/portfolio-interpretation-section", () => ({ PortfolioInterpretationSection: () => null }));
vi.mock("../components/repository-analysis-section", () => ({ RepositoryAnalysisSection: () => null }));
vi.mock("../components/analysis-history", () => ({ AnalysisHistory: () => null }));
vi.mock("../components/ai-suggested-actions", () => ({ AISuggestedActions: () => null }));
vi.mock("../components/action-plan", () => ({ ActionPlan: () => null }));

function response(isOwner: boolean): GitHubPortfolioInterpretationResponse {
  return {
    analysis: {
      user: { username: "target", name: null, html_url: "", public_repos: 0 } as never,
      selection: { excluded: [] } as never,
      repository_analysis: { repositories: [], failures: [] } as never,
      aggregation: { has_failures: false, selected_repository_count: 0, successful_repository_count: 0, failed_repository_count: 0, partial_evidence_repository_count: 0 } as never,
      intelligence: { limitations: [], strength_signals: [], improvement_signals: [], recurring_technologies: [], dominant_areas: [] } as never,
      score: { dimensions: [], limitations: [], is_partial: false, is_available: false, overall_score: null, scored_repository_count: 0 } as never,
    } as never,
    interpretation: { status: "unavailable", reason: "not_configured" },
    viewer_context: { is_owner: isOwner, mode: isOwner ? "my_workspace" : "explore" },
    guided_improvements: [{ rule_key: "readme_exists", title: "Sunucu rehberi", why: "why", steps: ["step"], verification: { detected_repository_count: 1, analyzed_repository_count: 1, current_state: "needs_improvement", analysis_available: true, analysis_partial: false, reanalysis_required: true } }],
  };
}

afterEach(cleanup);

describe("AnalysisResultShell Guided Improvement visibility", () => {
  it("renders owner guidance from viewer context", () => {
    render(<AnalysisResultShell result={response(true)} onReanalyze={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Guided Improvement" })).toBeInTheDocument();
  });

  it("does not render guidance for Explore even when a fixture contains items", () => {
    render(<AnalysisResultShell result={response(false)} onReanalyze={vi.fn()} />);
    expect(screen.queryByRole("heading", { name: "Guided Improvement" })).not.toBeInTheDocument();
  });
});
