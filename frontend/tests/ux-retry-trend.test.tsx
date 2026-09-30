import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisHistory } from "../components/analysis-history";
import { useAuth } from "../components/auth-provider";
import { PortfolioInterpretationSection } from "../components/portfolio-interpretation-section";
import { ScoreTrend, scorePoints } from "../components/score-trend";
import { getAnalysisHistory } from "../lib/api";
import type { GitHubPortfolioAnalysis, HistoryRecord, HistoryResponse, InterpretationUnavailableReason } from "../lib/types";

vi.mock("../components/auth-provider", () => ({ useAuth: vi.fn() }));
vi.mock("../lib/api", () => ({
  ApiError: class ApiError extends Error {},
  getAnalysisHistory: vi.fn(),
}));

afterEach(cleanup);

const analysis = { aggregation: { portfolio_signals: [] } } as unknown as GitHubPortfolioAnalysis;
const unavailable = (reason: InterpretationUnavailableReason) => ({ status: "unavailable", reason }) as const;

describe("PortfolioInterpretationSection retry", () => {
  it.each(["rate_limit", "timeout", "unavailable", "upstream_error"] as const)("offers a retry when the AI is unavailable because of %s", async (reason) => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<PortfolioInterpretationSection analysis={analysis} interpretation={unavailable(reason)} onRetry={onRetry} />);

    await user.click(screen.getByRole("button", { name: "AI yorumunu yeniden dene" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/bir dakika kadar bekleyip/)).toBeInTheDocument();
  });

  it.each(["not_configured", "insufficient_evidence", "invalid_response"] as const)("does not offer a pointless retry for %s", (reason) => {
    render(<PortfolioInterpretationSection analysis={analysis} interpretation={unavailable(reason)} onRetry={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "AI yorumunu yeniden dene" })).not.toBeInTheDocument();
  });

  it("shows no retry when the caller cannot retry", () => {
    render(<PortfolioInterpretationSection analysis={analysis} interpretation={unavailable("rate_limit")} />);
    expect(screen.queryByRole("button", { name: "AI yorumunu yeniden dene" })).not.toBeInTheDocument();
    expect(screen.getByText("AI yorumu şu anda kullanılamıyor.")).toBeInTheDocument();
  });
});

const record = (id: string, score: number | null, capturedAt: string): HistoryRecord => ({
  id,
  github_user_id: 1,
  github_username: "alice",
  captured_at: capturedAt,
  analysis_version: "v1",
  analysis_schema_version: "v1",
  portfolio_score: score,
  category_scores: [],
  passed_checks: [],
  failed_checks: [],
});

describe("ScoreTrend", () => {
  it("orders points from oldest to newest whatever the input order and skips unscored analyses", () => {
    const points = scorePoints([
      record("c", 64, "2026-09-20T00:00:00Z"),
      record("x", null, "2026-09-10T00:00:00Z"),
      record("a", 41, "2026-09-01T00:00:00Z"),
      record("b", 55, "2026-09-10T12:00:00Z"),
    ]);
    expect(points.map((point) => point.score)).toEqual([41, 55, 64]);
  });

  it("describes the trend for screen readers and shows the net change", () => {
    render(<ScoreTrend history={[record("c", 64, "2026-09-20T00:00:00Z"), record("b", 55, "2026-09-10T00:00:00Z"), record("a", 41, "2026-09-01T00:00:00Z")]} />);

    expect(screen.getByRole("img")).toHaveAccessibleName("Skor geçmişi, en eskiden en yeniye: 41, 55, 64. 23 puan arttı.");
    expect(screen.getByText("+23 puan")).toBeInTheDocument();
    expect(screen.getByText("Skor eğilimi")).toBeInTheDocument();
  });

  it("reports a decrease and no change", () => {
    const { unmount } = render(<ScoreTrend history={[record("a", 70, "2026-09-01T00:00:00Z"), record("b", 62, "2026-09-02T00:00:00Z")]} />);
    expect(screen.getByText("−8 puan")).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAccessibleName(/8 puan azaldı/);
    unmount();

    render(<ScoreTrend history={[record("a", 50, "2026-09-01T00:00:00Z"), record("b", 50, "2026-09-02T00:00:00Z")]} />);
    expect(screen.getByText("Değişmedi", { selector: "span" })).toBeInTheDocument();
  });

  it("draws one marker per analysis and highlights the latest", () => {
    const { container } = render(<ScoreTrend history={[record("a", 41, "2026-09-01T00:00:00Z"), record("b", 55, "2026-09-02T00:00:00Z"), record("c", 64, "2026-09-03T00:00:00Z")]} />);
    const circles = container.querySelectorAll("svg circle");
    expect(circles).toHaveLength(3);
    expect(circles[2].getAttribute("r")).toBe("4.5");
    expect(circles[0].getAttribute("r")).toBe("3");
    expect(container.querySelector("polyline")?.getAttribute("points")?.split(" ")).toHaveLength(3);
  });

  it("stays hidden with fewer than two scored analyses", () => {
    expect(render(<ScoreTrend history={[]} />).container).toBeEmptyDOMElement();
    cleanup();
    expect(render(<ScoreTrend history={[record("a", 50, "2026-09-01T00:00:00Z")]} />).container).toBeEmptyDOMElement();
    cleanup();
    expect(render(<ScoreTrend history={[record("a", 50, "2026-09-01T00:00:00Z"), record("b", null, "2026-09-02T00:00:00Z")]} />).container).toBeEmptyDOMElement();
  });

  it("keeps points on the fixed 0-100 scale", () => {
    const { container } = render(<ScoreTrend history={[record("a", 0, "2026-09-01T00:00:00Z"), record("b", 100, "2026-09-02T00:00:00Z")]} />);
    const [low, high] = Array.from(container.querySelectorAll("svg circle")).map((circle) => Number(circle.getAttribute("cy")));
    expect(low).toBeGreaterThan(high);
    expect(high).toBeGreaterThanOrEqual(0);
    expect(low).toBeLessThanOrEqual(96);
  });
});

describe("AnalysisHistory trend chart", () => {
  const mockedAuth = vi.mocked(useAuth);
  const mockedGet = vi.mocked(getAnalysisHistory);

  beforeEach(() => {
    vi.clearAllMocks();
    mockedAuth.mockReturnValue({ status: "authenticated", user: { github_login: "alice", display_name: "Alice", avatar_url: null, github_html_url: null }, errorMessage: null, refresh: vi.fn(), logout: vi.fn() });
  });

  it("shows the trend once there are at least two scored analyses", async () => {
    const history = [record("b", 68, "2026-09-02T00:00:00Z"), record("a", 61, "2026-08-15T00:00:00Z")];
    const data: HistoryResponse = { latest: history[0], previous: history[1], comparison: { portfolio_score: 7, category_scores: [], newly_passing_checks: [], newly_failing_checks: [], comparable: true, note: null }, history };
    mockedGet.mockResolvedValue(data);
    render(<AnalysisHistory visible />);

    expect(await screen.findByRole("img", { name: /Skor geçmişi, en eskiden en yeniye: 61, 68/ })).toBeInTheDocument();
    expect(screen.getByText("+7 puan")).toBeInTheDocument();
  });

  it("does not draw a chart for the first analysis", async () => {
    const only = record("a", 61, "2026-08-15T00:00:00Z");
    mockedGet.mockResolvedValue({ latest: only, previous: null, comparison: null, history: [only] });
    render(<AnalysisHistory visible />);

    await waitFor(() => expect(screen.getByText(/başlangıç noktanız/i)).toBeInTheDocument());
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
