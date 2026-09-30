import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisResultShell } from "../components/analysis-result-shell";
import type { GitHubPortfolioInterpretationResponse } from "../lib/types";

const mockedUseAuth = vi.hoisted(() => vi.fn());

vi.mock("../components/auth-provider", () => ({ useAuth: mockedUseAuth }));
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

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
  mockedUseAuth.mockReturnValue({ status: "authenticated", user: { github_login: "alice" } });
});
afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
});

describe("AnalysisResultShell tabs and Yönlendirmeli İyileştirme görünürlüğü", () => {
  it("shows the overview tab first and keeps other panels hidden", () => {
    render(<AnalysisResultShell result={response(true)} onReanalyze={vi.fn()} />);
    expect(screen.getByRole("tab", { name: /Genel Bakış/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: /Genel Bakış/ })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Yönlendirmeli İyileştirme" })).not.toBeInTheDocument();
  });

  it("renders owner guidance in the Aksiyonlar tab from viewer context", async () => {
    const user = userEvent.setup();
    render(<AnalysisResultShell result={response(true)} onReanalyze={vi.fn()} />);
    await user.click(screen.getByRole("tab", { name: /Aksiyonlar/ }));
    expect(screen.getByRole("heading", { name: "Yönlendirmeli İyileştirme" })).toBeInTheDocument();
  });

  it("keeps the Aksiyonlar tab locked for Explore even when a fixture contains items", async () => {
    const user = userEvent.setup();
    render(<AnalysisResultShell result={response(false)} onReanalyze={vi.fn()} />);

    const tab = screen.getByRole("tab", { name: /Aksiyonlar/ });
    expect(tab).toHaveTextContent("(giriş gerekli)");
    await user.click(tab);
    expect(screen.queryByRole("heading", { name: "Yönlendirmeli İyileştirme" })).not.toBeInTheDocument();
    expect(screen.getByRole("tabpanel", { name: /Aksiyonlar/ })).toBeVisible();
  });

  it("invites an anonymous visitor to sign in from the locked tab", async () => {
    mockedUseAuth.mockReturnValue({ status: "anonymous", user: null });
    const user = userEvent.setup();
    render(<AnalysisResultShell result={response(false)} onReanalyze={vi.fn()} />);
    await user.click(screen.getByRole("tab", { name: /Aksiyonlar/ }));

    expect(screen.getByRole("heading", { name: "Aksiyonların kilidini aç" })).toBeInTheDocument();
    expect(screen.getByText("İlerleme geçmişi")).toBeInTheDocument();
    expect(screen.getByText("AI önerilen aksiyonlar")).toBeInTheDocument();
    expect(screen.getByText("Aksiyon planı")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "GitHub ile giriş yap" })).toHaveAttribute("href", "http://localhost:8000/api/v1/auth/github");
  });

  it("points a signed-in visitor to their own portfolio instead of the sign-in link", async () => {
    const user = userEvent.setup();
    render(<AnalysisResultShell result={response(false)} onReanalyze={vi.fn()} />);
    await user.click(screen.getByRole("tab", { name: /Aksiyonlar/ }));

    expect(screen.getByRole("heading", { name: "Aksiyonlar yalnızca kendi portföyünde açılır" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Kendi portföyünü analiz et" })).toHaveAttribute("href", "/?workspace=1&username=alice");
    expect(screen.queryByRole("link", { name: "GitHub ile giriş yap" })).not.toBeInTheDocument();
  });

  it("does not lock the tab for the portfolio owner", () => {
    render(<AnalysisResultShell result={response(true)} onReanalyze={vi.fn()} />);
    expect(screen.getByRole("tab", { name: /Aksiyonlar/ })).not.toHaveTextContent("(giriş gerekli)");
  });

  it("supports arrow, Home and End keyboard navigation between tabs", async () => {
    const user = userEvent.setup();
    render(<AnalysisResultShell result={response(true)} onReanalyze={vi.fn()} />);
    screen.getByRole("tab", { name: /Genel Bakış/ }).focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: /Repository'ler/ })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: /Aksiyonlar/ })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: /Genel Bakış/ })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: /Genel Bakış/ })).toHaveFocus();
  });
});
