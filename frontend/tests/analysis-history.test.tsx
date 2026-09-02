import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisHistory } from "../components/analysis-history";
import { useAuth } from "../components/auth-provider";
import { getAnalysisHistory } from "../lib/api";
import type { HistoryResponse } from "../lib/types";

vi.mock("../components/auth-provider", () => ({ useAuth: vi.fn() }));
vi.mock("../lib/api", () => ({
  ApiError: class ApiError extends Error {},
  getAnalysisHistory: vi.fn(),
}));

const mockedAuth = vi.mocked(useAuth);
const mockedGet = vi.mocked(getAnalysisHistory);
const user = { github_login: "alice", display_name: "Alice", avatar_url: null, github_html_url: null };
const record = (id: string, score: number, date: string) => ({ id, github_user_id: 1, github_username: "alice", captured_at: date, analysis_version: "v1", analysis_schema_version: "v1", portfolio_score: score, category_scores: [], passed_checks: [], failed_checks: [] });

describe("Analysis history privacy and progress UI", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    vi.clearAllMocks();
    mockedAuth.mockReturnValue({ status: "authenticated", user, errorMessage: null, refresh: vi.fn(), logout: vi.fn() });
  });

  it("shows owner baseline and stays absent outside workspace", async () => {
    mockedGet.mockResolvedValue({ latest: record("a", 61, "2026-08-15T00:00:00Z"), previous: null, comparison: null, history: [record("a", 61, "2026-08-15T00:00:00Z")] });
    const { rerender } = render(<AnalysisHistory visible />);
    expect(await screen.findByText(/baseline/i)).toBeInTheDocument();
    rerender(<AnalysisHistory visible={false} />);
    expect(screen.queryByText("İlerleme")).not.toBeInTheDocument();
  });

  it("renders latest, previous and deterministic delta", async () => {
    const data: HistoryResponse = { latest: record("b", 68, "2026-09-02T00:00:00Z"), previous: record("a", 61, "2026-08-15T00:00:00Z"), comparison: { portfolio_score: 7, category_scores: [], newly_passing_checks: [], newly_failing_checks: [], comparable: true, note: null }, history: [record("b", 68, "2026-09-02T00:00:00Z"), record("a", 61, "2026-08-15T00:00:00Z")] };
    mockedGet.mockResolvedValue(data);
    render(<AnalysisHistory visible />);
    expect(await screen.findByText("+7")).toBeInTheDocument();
    expect(screen.getAllByText("68")).toHaveLength(2);
    expect(screen.getAllByText("61")).toHaveLength(2);
  });

  it("ignores a late response after leaving workspace", async () => {
    let resolveA: (value: HistoryResponse) => void = () => undefined;
    mockedGet.mockReturnValueOnce(new Promise((done) => { resolveA = done; })).mockResolvedValueOnce({ latest: record("b", 68, "2026-09-02T00:00:00Z"), previous: null, comparison: null, history: [] });
    const { rerender } = render(<AnalysisHistory visible />);
    rerender(<AnalysisHistory visible={false} />);
    rerender(<AnalysisHistory visible />);
    resolveA({ latest: record("a", 99, "2026-09-02T00:00:00Z"), previous: null, comparison: null, history: [] });
    await waitFor(() => expect(screen.getByText("68")).toBeInTheDocument());
    expect(screen.queryByText("99")).not.toBeInTheDocument();
  });
});
