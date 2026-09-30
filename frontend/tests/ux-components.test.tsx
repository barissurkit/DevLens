import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AnalysisLoadingState } from "../components/analysis-loading-state";
import { FreshnessNote, formatAge } from "../components/freshness-note";
import { PortfolioOverview } from "../components/portfolio-overview";
import { ScoreMethodology, rulePoints } from "../components/score-methodology";
import type { GitHubPortfolioAnalysis, PortfolioScoreDimensionResult } from "../lib/types";

afterEach(cleanup);

describe("AnalysisLoadingState progress", () => {
  it("falls back to the generic steps when no progress has been reported", () => {
    render(<AnalysisLoadingState />);
    expect(screen.getByText("Her repository için deterministik kanıtlar hesaplanır")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("shows repository progress with a progress bar", () => {
    render(<AnalysisLoadingState progress={{ stage: "repositories", completed: 2, total: 5 }} />);
    expect(screen.getByText("Repository'ler analiz ediliyor (2 / 5)")).toBeInTheDocument();
    const bar = screen.getByRole("progressbar", { name: "Repository analizi ilerlemesi" });
    expect(bar).toHaveAttribute("aria-valuenow", "2");
    expect(bar).toHaveAttribute("aria-valuemax", "5");
    expect(bar).toHaveAttribute("aria-valuetext", "2 / 5 repository");
    expect(screen.getByText(/GitHub profili ve repository listesi alınıyor/)).toBeInTheDocument();
    expect(screen.getByText("(tamamlandı)")).toBeInTheDocument();
    expect(screen.queryByText("AI yorumu hazırlanıyor")).not.toBeInTheDocument();
  });

  it("does not show a bar before the repository list is known", () => {
    render(<AnalysisLoadingState progress={{ stage: "profile", completed: 0, total: 0 }} />);
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(screen.queryByText("(tamamlandı)")).not.toBeInTheDocument();
  });

  it("marks earlier steps done and announces the AI step", () => {
    render(<AnalysisLoadingState progress={{ stage: "interpretation", completed: 0, total: 0 }} />);
    expect(screen.getByText("AI yorumu hazırlanıyor")).toBeInTheDocument();
    expect(screen.getAllByText("(tamamlandı)")).toHaveLength(2);
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });
});

describe("formatAge", () => {
  const now = Date.parse("2026-09-30T12:00:00Z");
  it.each([
    [10, "az önce"],
    [44, "az önce"],
    [4 * 60, "4 dakika önce"],
    [2 * 3600, "2 saat önce"],
    [3 * 86400, "3 gün önce"],
  ])("formats %i seconds", (seconds, expected) => {
    expect(formatAge(now - seconds * 1000, now)).toBe(expected);
  });

  it("never reports a negative age for clock skew", () => {
    expect(formatAge(now + 5000, now)).toBe("az önce");
  });
});

describe("FreshnessNote", () => {
  it("shows when the result was computed, whether it was cached, and refreshes on demand", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    const generatedAt = new Date(Date.now() - 4 * 60 * 1000).toISOString();
    render(<FreshnessNote generatedAt={generatedAt} cached onRefresh={onRefresh} />);

    expect(screen.getByText("4 dakika önce")).toBeInTheDocument();
    expect(screen.getByText(/önbellekten sunuldu/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Yenile" }));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("omits the cache label for a fresh computation", () => {
    render(<FreshnessNote generatedAt={new Date().toISOString()} cached={false} onRefresh={vi.fn()} />);
    expect(screen.getByText("az önce")).toBeInTheDocument();
    expect(screen.queryByText(/önbellekten/)).not.toBeInTheDocument();
  });

  it("renders nothing for an unparseable timestamp", () => {
    const { container } = render(<FreshnessNote generatedAt="not-a-date" cached={false} onRefresh={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

const dimensions: PortfolioScoreDimensionResult[] = [
  {
    key: "testing_automation_adoption",
    label: "Test ve Otomasyon",
    score: 40,
    points_earned: 12,
    points_possible: 30,
    rules: [
      { key: "tests_structure", label: "Test Yapısı", weight: 18, detected_repository_count: 2, analyzed_repository_count: 6 },
      { key: "ci_workflow", label: "CI İş Akışı", weight: 12, detected_repository_count: 6, analyzed_repository_count: 6 },
    ],
  },
];

describe("ScoreMethodology", () => {
  it("explains the formula with a worked example taken from the real data", () => {
    render(<ScoreMethodology dimensions={dimensions} scoredRepositoryCount={6} />);

    expect(screen.getByText("Skor nasıl hesaplanır?")).toBeInTheDocument();
    expect(screen.getByText(/ağırlık × \(sinyali olan repository \/ analiz edilen repository\)/)).toBeInTheDocument();
    // Test Yapısı is the first rule present in some but not all repositories: 18 × 2/6 = 6.
    const example = screen.getByText(/Örnek:/).closest("p");
    expect(example).toHaveTextContent("Test Yapısı (18 puan)");
    expect(example).toHaveTextContent("18 × 2/6");
    expect(example).toHaveTextContent("≈ 6 puan");
  });

  it("lists every rule with coverage and points", () => {
    render(<ScoreMethodology dimensions={dimensions} scoredRepositoryCount={6} />);
    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row");
    expect(within(rows[1]).getByText("Test Yapısı")).toBeInTheDocument();
    expect(within(rows[1]).getByText("2 / 6")).toBeInTheDocument();
    expect(within(rows[1]).getByText("6 / 18")).toBeInTheDocument();
    expect(within(rows[2]).getByText("6 / 6")).toBeInTheDocument();
    expect(within(rows[2]).getByText("12 / 12")).toBeInTheDocument();
  });

  it("states the constraints and colour bands", () => {
    render(<ScoreMethodology dimensions={dimensions} scoredRepositoryCount={6} />);
    expect(screen.getByText(/en az iki repository/)).toHaveTextContent("bu skor 6 repository üzerinden hesaplandı");
    expect(screen.getByText(/Fork edilmiş ve arşivlenmiş/)).toBeInTheDocument();
    expect(screen.getByText(/Yapay zekâ yorumu skoru/)).toBeInTheDocument();
    expect(screen.getByText(/Renk bantları/)).toHaveTextContent("75 ve üzeri Güçlü, 50–74 Gelişebilir, 50 altı Zayıf");
  });

  it("still explains the rules when no score could be computed", () => {
    render(<ScoreMethodology dimensions={[]} scoredRepositoryCount={0} />);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText(/Örnek:/)).not.toBeInTheDocument();
    expect(screen.getByText(/en az iki repository/)).toBeInTheDocument();
  });

  it("computes rule points as weight times coverage", () => {
    expect(rulePoints(dimensions[0].rules[0])).toBe(6);
    expect(rulePoints({ key: "x", label: "x", weight: 10, detected_repository_count: 0, analyzed_repository_count: 0 })).toBe(0);
  });
});

function overviewAnalysis(): GitHubPortfolioAnalysis {
  return {
    user: { username: "target", public_repos: 6 } as never,
    selection: { excluded: [] } as never,
    repository_analysis: { repositories: [], failures: [] } as never,
    aggregation: { has_failures: false, selected_repository_count: 6, successful_repository_count: 6, failed_repository_count: 0, partial_evidence_repository_count: 0 } as never,
    intelligence: {
      limitations: [],
      strength_signals: [{ key: "readme_exists", message: "README içeriği sinyalleri, güçlü.", detected_repository_count: 5, analyzed_repository_count: 6 }],
      improvement_signals: [{ key: "ci_workflow", message: "GitHub Actions iş akışı sinyalleri, sınırlı.", detected_repository_count: 2, analyzed_repository_count: 6 }],
      recurring_technologies: [],
      dominant_areas: [],
    } as never,
    score: { dimensions, limitations: [], is_partial: false, is_available: true, overall_score: 64, scored_repository_count: 6 } as never,
  } as GitHubPortfolioAnalysis;
}

describe("PortfolioOverview", () => {
  it("shows in how many repositories each signal was found", () => {
    render(<PortfolioOverview analysis={overviewAnalysis()} />);
    const strengths = screen.getByRole("region", { name: "Güçlü Kanıt Sinyalleri" });
    const improvements = screen.getByRole("region", { name: "Gelişim Alanları" });
    expect(within(strengths).getByText(/5 \/ 6 repository/)).toBeInTheDocument();
    expect(within(improvements).getByText(/2 \/ 6 repository/)).toBeInTheDocument();
    expect(within(improvements).getByText(/yaklaşık %33/)).toBeInTheDocument();
  });

  it("offers the score methodology next to the score", () => {
    render(<PortfolioOverview analysis={overviewAnalysis()} />);
    expect(screen.getByText("Skor nasıl hesaplanır?")).toBeInTheDocument();
  });
});
