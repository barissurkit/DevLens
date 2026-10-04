import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ComparisonView } from "../components/comparison-view";
import { comparePath } from "../lib/share";
import type { GitHubPortfolioAnalysis } from "../lib/types";

const push = vi.hoisted(() => vi.fn());
const analyze = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("../lib/api", () => ({
  analyzePortfolio: analyze,
  ApiError: class ApiError extends Error {
    constructor(message: string, readonly status: number, readonly code: string) {
      super(message);
    }
  },
}));

function portfolio(username: string, overall: number, docsDetected: number): GitHubPortfolioAnalysis {
  return {
    user: { username, name: null },
    score: {
      version: "v1",
      is_available: true,
      overall_score: overall,
      scored_repository_count: 4,
      is_partial: false,
      limitations: [],
      dimensions: [{
        key: "documentation_consistency",
        label: "Dokümantasyon",
        points_earned: overall / 2,
        points_possible: 50,
        score: overall,
        rules: [{ key: "readme_usage", label: "README kullanımı", weight: 9, detected_repository_count: docsDetected, analyzed_repository_count: 4 }],
      }],
    },
  } as unknown as GitHubPortfolioAnalysis;
}

beforeEach(() => {
  analyze.mockImplementation(async (username: string) => (username === "alice" ? portfolio("alice", 72, 4) : portfolio("bob", 48, 1)));
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("comparison form", () => {
  it("opens the comparison page for two valid, different users", () => {
    render(<ComparisonView />);

    fireEvent.change(screen.getByLabelText("Birinci kullanıcı"), { target: { value: "https://github.com/alice" } });
    fireEvent.change(screen.getByLabelText("İkinci kullanıcı"), { target: { value: "@bob" } });
    fireEvent.click(screen.getByRole("button", { name: "Karşılaştır" }));

    expect(push).toHaveBeenCalledWith(comparePath("alice", "bob"));
    expect(analyze).not.toHaveBeenCalled();
  });

  it.each([
    ["", "bob", "Birinci kullanıcı: Bir GitHub kullanıcı adı girin."],
    ["alice", "-bad", "İkinci kullanıcı:"],
    ["Alice", "alice", "iki farklı kullanıcı"],
  ])("rejects %j and %j", (first, second, message) => {
    render(<ComparisonView />);
    fireEvent.change(screen.getByLabelText("Birinci kullanıcı"), { target: { value: first } });
    fireEvent.change(screen.getByLabelText("İkinci kullanıcı"), { target: { value: second } });
    fireEvent.click(screen.getByRole("button", { name: "Karşılaştır" }));

    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(push).not.toHaveBeenCalled();
  });
});

describe("comparison result", () => {
  it("analyzes both users in order and shows the verdict, bars, rule table and gaps", async () => {
    render(<ComparisonView a="alice" b="bob" />);

    await waitFor(() => expect(screen.getByText(/portföyünden 24 puan önde/)).toBeInTheDocument());
    expect(analyze.mock.calls.map((call) => call[0])).toEqual(["alice", "bob"]);
    expect(screen.getByText("72 / 100")).toBeInTheDocument();
    expect(screen.getByText("48 / 100")).toBeInTheDocument();
    expect(screen.getByText("Önde", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toHaveTextContent("README kullanımı");
    expect(screen.getByRole("table")).toHaveTextContent("4 / 4");
    expect(screen.getByRole("table")).toHaveTextContent("1 / 4");
    expect(screen.getByRole("heading", { name: "@bob için fırsatlar" })).toBeInTheDocument();
    expect(screen.getByText("@bob portföyünün belirgin biçimde önde olduğu bir kriter yok.")).toBeInTheDocument();
    expect(screen.getByText("@alice portföyünün daha tutarlı olduğu kriterler:")).toBeInTheDocument();
  });

  it("says which user could not be analyzed", async () => {
    const { ApiError } = await import("../lib/api");
    analyze.mockImplementation(async (username: string) => {
      if (username === "bob") throw new ApiError("yok", 404, "github_user_not_found");
      return portfolio("alice", 72, 4);
    });
    render(<ComparisonView a="alice" b="bob" />);

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("@bob: GitHub kullanıcısı bulunamadı."));
  });

  it("explains a rate limit", async () => {
    const { ApiError } = await import("../lib/api");
    analyze.mockRejectedValue(new ApiError("x", 429, "rate_limited"));
    render(<ComparisonView a="alice" b="bob" />);

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("@alice: Çok fazla istek gönderildi"));
  });

  it("does not start anything with only one user", async () => {
    render(<ComparisonView a="alice" />);
    await new Promise((resolve) => setTimeout(resolve, 30));

    expect(analyze).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Birinci kullanıcı")).toHaveValue("alice");
  });
});
