import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisForm } from "../components/analysis-form";
import type { GitHubPortfolioInterpretationResponse } from "../lib/types";

const mockedAnalyze = vi.hoisted(() => vi.fn());
const mockedUseAuth = vi.hoisted(() => vi.fn());

vi.mock("../lib/api", () => ({
  analyzePortfolioWithInterpretation: mockedAnalyze,
  ApiError: class ApiError extends Error {},
}));
vi.mock("../components/auth-provider", () => ({ useAuth: mockedUseAuth }));
vi.mock("../components/analysis-result-shell", () => ({
  AnalysisResultShell: ({ result, onReanalyze, onRetryInterpretation }: { result: GitHubPortfolioInterpretationResponse; onReanalyze: () => void; onRetryInterpretation?: () => void }) => (
    <div data-testid="result-shell">
      {result.analysis.user.username}
      <button type="button" onClick={onReanalyze}>Yenile</button>
      <button type="button" onClick={onRetryInterpretation}>AI yorumunu yeniden dene</button>
    </div>
  ),
}));

const input = () => screen.getByLabelText("GitHub kullanıcı adı") as HTMLInputElement;

function type(value: string) {
  fireEvent.change(input(), { target: { value } });
}

function submit() {
  fireEvent.submit(input().closest("form")!);
}

describe("AnalysisForm input handling", () => {
  beforeEach(() => {
    mockedUseAuth.mockReturnValue({ status: "anonymous", user: null });
    mockedAnalyze.mockImplementation(async (username: string) => ({ analysis: { user: { username } } }));
  });
  afterEach(() => { cleanup(); vi.clearAllMocks(); });

  it.each([
    ["https://github.com/octocat", "octocat"],
    ["github.com/octocat/Hello-World", "octocat"],
    ["@octocat", "octocat"],
    ["  octocat  ", "octocat"],
  ])("analyzes the login extracted from %s", async (typed, expected) => {
    render(<AnalysisForm />);
    type(typed);
    submit();

    await waitFor(() => expect(screen.getByTestId("result-shell")).toHaveTextContent(expected));
    expect(mockedAnalyze).toHaveBeenCalledWith(expected, expect.anything());
  });

  it("shows the plain username back in the field after submitting a link", async () => {
    render(<AnalysisForm />);
    type("https://github.com/torvalds");
    submit();

    await waitFor(() => expect(input().value).toBe("torvalds"));
  });

  it("explains invalid characters while typing without blocking partial input", () => {
    render(<AnalysisForm />);

    type("octo cat");
    expect(screen.getByText("Yalnızca harf, rakam ve tire kullanılabilir.")).toBeInTheDocument();

    type("octo-");
    expect(screen.queryByText("Yalnızca harf, rakam ve tire kullanılabilir.")).not.toBeInTheDocument();
    expect(screen.getByText(/@kullanici veya bir github.com\/kullanici/)).toBeInTheDocument();
  });

  it("rejects an invalid login on submit without calling the API", () => {
    render(<AnalysisForm />);
    type("-octocat");
    submit();

    expect(screen.getByRole("alert")).toHaveTextContent("tire ile başlayıp bitemez");
    expect(mockedAnalyze).not.toHaveBeenCalled();
  });

  it("keeps the existing messages for an empty and an over-long value", () => {
    render(<AnalysisForm />);
    type("   ");
    submit();
    expect(screen.getByRole("alert")).toHaveTextContent("Bir GitHub kullanıcı adı girin.");

    type("a".repeat(40));
    submit();
    expect(screen.getByRole("alert")).toHaveTextContent("GitHub kullanıcı adı 39 karakterden uzun olamaz.");
    expect(mockedAnalyze).not.toHaveBeenCalled();
  });

  it("starts an analysis straight from an example username", async () => {
    render(<AnalysisForm />);
    fireEvent.click(screen.getByRole("button", { name: "octocat" }));

    await waitFor(() => expect(screen.getByTestId("result-shell")).toHaveTextContent("octocat"));
    expect(mockedAnalyze).toHaveBeenCalledWith("octocat", expect.anything());
  });

  it("hides the examples once a result is shown", async () => {
    render(<AnalysisForm />);
    expect(screen.getByText("Örnek dene:")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "torvalds" }));

    await waitFor(() => expect(screen.getByTestId("result-shell")).toBeInTheDocument());
    expect(screen.queryByText("Örnek dene:")).not.toBeInTheDocument();
  });

  it("shows streamed progress while the analysis is running", async () => {
    let finish: (value: unknown) => void = () => undefined;
    mockedAnalyze.mockImplementation((_username: string, options: { onProgress: (p: unknown) => void }) => {
      options.onProgress({ stage: "repositories", completed: 1, total: 4 });
      return new Promise((resolve) => { finish = resolve; });
    });
    render(<AnalysisForm />);
    type("octocat");
    submit();

    expect(await screen.findByText("Repository'ler analiz ediliyor (1 / 4)")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Repository analizi ilerlemesi" })).toHaveAttribute("aria-valuenow", "1");

    finish({ analysis: { user: { username: "octocat" } } });
    await waitFor(() => expect(screen.getByTestId("result-shell")).toBeInTheDocument());
  });

  it("aborts an in-flight request when the form goes away", async () => {
    const signals: AbortSignal[] = [];
    mockedAnalyze.mockImplementation((_username: string, options: { signal: AbortSignal }) => {
      signals.push(options.signal);
      return new Promise(() => undefined);
    });
    render(<AnalysisForm />);
    type("alice");
    submit();
    await waitFor(() => expect(signals).toHaveLength(1));
    expect(signals[0].aborted).toBe(false);

    // Leaving the page must cancel the request so the backend stops working for nobody.
    cleanup();
    expect(signals[0].aborted).toBe(true);
  });

  it("retries only the AI interpretation without bypassing the cache, while Yenile does bypass it", async () => {
    render(<AnalysisForm />);
    type("octocat");
    submit();
    await waitFor(() => expect(screen.getByTestId("result-shell")).toBeInTheDocument());
    expect(mockedAnalyze).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "AI yorumunu yeniden dene" }));
    await waitFor(() => expect(mockedAnalyze).toHaveBeenCalledTimes(2));
    expect(mockedAnalyze).toHaveBeenNthCalledWith(2, "octocat", expect.objectContaining({ refresh: undefined, retryInterpretation: true }));
    await waitFor(() => expect(screen.getByTestId("result-shell")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Yenile" }));
    await waitFor(() => expect(mockedAnalyze).toHaveBeenCalledTimes(3));
    expect(mockedAnalyze).toHaveBeenNthCalledWith(3, "octocat", expect.objectContaining({ refresh: true, retryInterpretation: undefined }));
  });
});

