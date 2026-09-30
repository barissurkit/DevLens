import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { ImprovementPriorities } from "../components/improvement-priorities";
import { PortfolioOverview } from "../components/portfolio-overview";
import { SignalDetail } from "../components/signal-detail";
import { topImprovements } from "../lib/priorities";
import { absenceMayBeIncomplete, repositoryHasSignal, splitRepositoriesBySignal } from "../lib/signals";
import type { GitHubPortfolioAnalysis, PortfolioRepositoryResult, PortfolioScoreDimensionResult } from "../lib/types";

afterEach(cleanup);

interface RepoOptions {
  readme?: Partial<Record<"exists" | "has_title" | "has_description" | "has_installation" | "has_usage" | "has_technologies" | "has_requirements", boolean>>;
  structure?: Partial<Record<"has_tests" | "has_ci" | "has_gitignore" | "has_license" | "has_contributing", boolean>>;
  truncated?: boolean;
}

function repo(name: string, options: RepoOptions = {}): PortfolioRepositoryResult {
  return {
    repository: { name, html_url: `https://github.com/demo/${name}` } as never,
    score: { overall_score: 50, dimensions: [], is_partial: false, limitations: [], version: "1" },
    analysis: {
      repository: {} as never,
      readme: { exists: true, content_length: 1, has_title: true, has_description: true, has_installation: false, has_usage: false, has_technologies: false, has_requirements: false, has_images: false, has_demo_link: false, ...options.readme },
      structure: { has_tests: false, has_ci: false, has_dockerfile: false, has_compose: false, has_env_example: false, has_license: false, has_gitignore: true, has_contributing: false, ...options.structure },
      tree_truncated: options.truncated ?? false,
      technologies: { dependencies: [], technologies: [] },
      classification: { categories: [], primary_category: "Backend" },
    } as never,
  };
}

describe("repositoryHasSignal", () => {
  it("reads README and structure signals from the repository analysis", () => {
    const withEverything = repo("a", {
      readme: { has_installation: true, has_usage: true, has_technologies: true, has_requirements: true },
      structure: { has_tests: true, has_ci: true, has_license: true, has_contributing: true },
    });
    for (const key of ["readme_exists", "readme_title", "readme_description", "readme_installation", "readme_usage", "readme_technologies", "readme_requirements", "tests_structure", "ci_workflow", "gitignore", "license", "contributing"]) {
      expect(repositoryHasSignal(withEverything, key), key).toBe(true);
    }
    const bare = repo("b");
    expect(repositoryHasSignal(bare, "readme_usage")).toBe(false);
    expect(repositoryHasSignal(bare, "ci_workflow")).toBe(false);
  });

  it("returns null for unknown signals", () => {
    expect(repositoryHasSignal(repo("a"), "not_a_signal")).toBeNull();
    expect(splitRepositoriesBySignal([repo("a")], "not_a_signal")).toBeNull();
  });

  it("splits repositories into those with and without the signal, keeping their order", () => {
    const repositories = [repo("a", { structure: { has_ci: true } }), repo("b"), repo("c", { structure: { has_ci: true } })];
    const split = splitRepositoriesBySignal(repositories, "ci_workflow");
    expect(split?.present.map((r) => r.repository.name)).toEqual(["a", "c"]);
    expect(split?.missing.map((r) => r.repository.name)).toEqual(["b"]);
  });

  it("only doubts structure signals when the tree was truncated", () => {
    expect(absenceMayBeIncomplete(repo("a", { truncated: true }), "ci_workflow")).toBe(true);
    expect(absenceMayBeIncomplete(repo("a", { truncated: true }), "readme_usage")).toBe(false);
    expect(absenceMayBeIncomplete(repo("a"), "ci_workflow")).toBe(false);
  });
});

const dimensions: PortfolioScoreDimensionResult[] = [
  {
    key: "docs",
    label: "Docs",
    score: 0,
    points_earned: 0,
    points_possible: 0,
    rules: [
      { key: "readme_exists", label: "README mevcut", weight: 8, detected_repository_count: 8, analyzed_repository_count: 8 },
      { key: "readme_usage", label: "README kullanımı", weight: 9, detected_repository_count: 2, analyzed_repository_count: 8 },
    ],
  },
  {
    key: "tests",
    label: "Tests",
    score: 0,
    points_earned: 0,
    points_possible: 0,
    rules: [
      { key: "tests_structure", label: "Test Yapısı", weight: 18, detected_repository_count: 2, analyzed_repository_count: 8 },
      { key: "ci_workflow", label: "CI İş Akışı", weight: 12, detected_repository_count: 0, analyzed_repository_count: 8 },
      { key: "contributing", label: "CONTRIBUTING", weight: 5, detected_repository_count: 0, analyzed_repository_count: 8 },
    ],
  },
];

describe("topImprovements", () => {
  it("ranks rules by the points they could still add and skips complete rules", () => {
    const result = topImprovements(dimensions);
    expect(result.map((item) => item.key)).toEqual(["tests_structure", "ci_workflow", "readme_usage"]);
    expect(result.map((item) => item.points)).toEqual([13.5, 12, 6.75]);
    expect(result[0]).toMatchObject({ missingRepositories: 6, analyzedRepositories: 8, weight: 18 });
  });

  it("honours the limit and ignores rules without analyzed repositories", () => {
    expect(topImprovements(dimensions, 1)).toHaveLength(1);
    expect(topImprovements([{ ...dimensions[0], rules: [{ key: "x", label: "x", weight: 10, detected_repository_count: 0, analyzed_repository_count: 0 }] }])).toEqual([]);
  });

  it("returns nothing when every rule is fully covered", () => {
    const complete = [{ ...dimensions[0], rules: [dimensions[0].rules[0]] }];
    expect(topImprovements(complete)).toEqual([]);
  });

  it("breaks ties by weight and then by label", () => {
    const tied = [{
      ...dimensions[0],
      rules: [
        { key: "b", label: "B", weight: 5, detected_repository_count: 0, analyzed_repository_count: 2 },
        { key: "a", label: "A", weight: 5, detected_repository_count: 0, analyzed_repository_count: 2 },
        { key: "c", label: "C", weight: 10, detected_repository_count: 1, analyzed_repository_count: 2 },
      ],
    }];
    // All three could add 5 points; the heavier rule (c) wins, then labels decide (a before b).
    expect(topImprovements(tied).map((item) => item.key)).toEqual(["c", "a", "b"]);
  });
});

describe("ImprovementPriorities", () => {
  it("shows the three most valuable steps with points and the combined gain", () => {
    render(<ImprovementPriorities dimensions={dimensions} overallScore={40} />);

    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("Test Yapısı");
    expect(items[0]).toHaveTextContent("8 repository'nin 6 tanesinde eksik");
    expect(items[0]).toHaveTextContent("+13,5 puan");
    expect(items[1]).toHaveTextContent("CI İş Akışı");
    expect(items[2]).toHaveTextContent("+6,8 puan");
    // 13.5 + 12 + 6.75 = 32.25, below the 60 points that are still available.
    expect(screen.getByText(/yaklaşık/)).toHaveTextContent("+32 puan");
  });

  it("never promises more than the points that are left up to 100", () => {
    render(<ImprovementPriorities dimensions={dimensions} overallScore={90} />);
    expect(screen.getByText(/yaklaşık/)).toHaveTextContent("+10 puan");
  });

  it("renders nothing when there is nothing left to improve", () => {
    const { container } = render(<ImprovementPriorities dimensions={[{ ...dimensions[0], rules: [dimensions[0].rules[0]] }]} overallScore={100} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("SignalDetail", () => {
  it("lists repositories that have and lack the signal with links", async () => {
    const user = userEvent.setup();
    const repositories = [repo("has-ci", { structure: { has_ci: true } }), repo("no-ci-a"), repo("no-ci-b", { truncated: true })];
    render(<SignalDetail signalKey="ci_workflow" repositories={repositories} />);

    await user.click(screen.getByText("Hangi repository'lerde?"));
    expect(screen.getByText("Var (1)")).toBeInTheDocument();
    expect(screen.getByText("Yok (2)")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "has-ci" })).toHaveAttribute("href", "https://github.com/demo/has-ci");
    expect(screen.getByRole("link", { name: "no-ci-a" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /no-ci-b/ })).toHaveTextContent("kısmi kanıt");
    expect(screen.getByRole("link", { name: "no-ci-a" })).not.toHaveTextContent("kısmi kanıt");
  });

  it("says when a group is empty", () => {
    render(<SignalDetail signalKey="readme_exists" repositories={[repo("only")]} />);
    expect(screen.getByText("Yok (0)").closest("div")).toHaveTextContent("Bu gruptaki repository yok.");
  });

  it("renders nothing without repositories or for an unknown signal", () => {
    const empty = render(<SignalDetail signalKey="ci_workflow" repositories={[]} />);
    expect(empty.container).toBeEmptyDOMElement();
    const unknown = render(<SignalDetail signalKey="mystery" repositories={[repo("a")]} />);
    expect(unknown.container).toBeEmptyDOMElement();
  });
});

describe("PortfolioOverview integration", () => {
  function analysis(): GitHubPortfolioAnalysis {
    const repositories = [repo("alpha", { structure: { has_ci: true } }), repo("bravo")];
    return {
      user: { username: "demo", public_repos: 2 } as never,
      selection: { excluded: [] } as never,
      repository_analysis: { repositories, failures: [] } as never,
      aggregation: { has_failures: false, selected_repository_count: 2, successful_repository_count: 2, failed_repository_count: 0, partial_evidence_repository_count: 0 } as never,
      intelligence: {
        limitations: [],
        strength_signals: [],
        improvement_signals: [{ key: "ci_workflow", message: "CI sınırlı.", detected_repository_count: 1, analyzed_repository_count: 2 }],
        recurring_technologies: [],
        dominant_areas: [],
      } as never,
      score: { dimensions, limitations: [], is_partial: false, is_available: true, overall_score: 40, scored_repository_count: 2 } as never,
    } as GitHubPortfolioAnalysis;
  }

  it("shows the priorities card and per-signal repository lists", () => {
    render(<PortfolioOverview analysis={analysis()} />);
    expect(screen.getByRole("region", { name: "Önce şunu yap" })).toBeInTheDocument();
    const improvements = screen.getByRole("region", { name: "Gelişim Alanları" });
    expect(within(improvements).getByText("Hangi repository'lerde?")).toBeInTheDocument();
    expect(within(improvements).getByRole("link", { name: "alpha" })).toBeInTheDocument();
  });

  it("hides the priorities card when no score is available", () => {
    const unavailable = analysis();
    unavailable.score = { ...unavailable.score, is_available: false, overall_score: null };
    render(<PortfolioOverview analysis={unavailable} />);
    expect(screen.queryByRole("region", { name: "Önce şunu yap" })).not.toBeInTheDocument();
  });
});
