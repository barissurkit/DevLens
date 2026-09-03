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
  AnalysisResultShell: ({ result, onReanalyze }: { result: GitHubPortfolioInterpretationResponse; onReanalyze: () => void }) => <div data-testid="result-shell"><span>{result.analysis.user.username}</span><button type="button" onClick={onReanalyze}>Tekrar analiz et</button></div>,
}));

function result(username: string): GitHubPortfolioInterpretationResponse {
  return { analysis: { user: { username } } } as GitHubPortfolioInterpretationResponse;
}

function deferred<T>() {
  let resolve: (value: T) => void = () => undefined;
  const promise = new Promise<T>((complete) => { resolve = complete; });
  return { promise, resolve };
}

function submit(username: string) {
  fireEvent.change(screen.getByLabelText("GitHub kullanıcı adı"), { target: { value: username } });
  fireEvent.submit(screen.getByLabelText("GitHub kullanıcı adı").closest("form")!);
}

describe("AnalysisForm lifecycle protection", () => {
  beforeEach(() => mockedUseAuth.mockReturnValue({ status: "authenticated", user: { github_login: "alice" } }));
  afterEach(() => { cleanup(); vi.clearAllMocks(); vi.restoreAllMocks(); });

  it("only applies the newest overlapping target request", async () => {
    const first = deferred<GitHubPortfolioInterpretationResponse>();
    const second = deferred<GitHubPortfolioInterpretationResponse>();
    mockedAnalyze.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    render(<AnalysisForm />);
    submit("alice");
    submit("bob");
    second.resolve(result("bob"));
    await waitFor(() => expect(screen.getByTestId("result-shell")).toHaveTextContent("bob"));
    first.resolve(result("alice"));
    await waitFor(() => expect(screen.getByTestId("result-shell")).toHaveTextContent("bob"));
  });

  it("clears and ignores an owner response that resolves after logout", async () => {
    const request = deferred<GitHubPortfolioInterpretationResponse>();
    mockedAnalyze.mockReturnValue(request.promise);
    const view = render(<AnalysisForm />);
    submit("alice");
    mockedUseAuth.mockReturnValue({ status: "anonymous", user: null });
    view.rerender(<AnalysisForm />);
    request.resolve(result("alice"));
    await waitFor(() => expect(screen.queryByTestId("result-shell")).not.toBeInTheDocument());
  });

  it("invalidates an in-flight response when authenticated identity changes", async () => {
    const request = deferred<GitHubPortfolioInterpretationResponse>();
    mockedAnalyze.mockReturnValue(request.promise);
    const view = render(<AnalysisForm />);
    submit("alice");
    mockedUseAuth.mockReturnValue({ status: "authenticated", user: { github_login: "bob" } });
    view.rerender(<AnalysisForm />);
    request.resolve(result("alice"));
    await waitFor(() => expect(screen.queryByTestId("result-shell")).not.toBeInTheDocument());
  });

  it("routes re-analysis through the parent analysis request", async () => {
    mockedAnalyze.mockResolvedValueOnce(result("alice")).mockReturnValueOnce(new Promise(() => undefined));
    render(<AnalysisForm />);
    submit("alice");
    await waitFor(() => expect(screen.getByTestId("result-shell")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Tekrar analiz et" }));
    expect(mockedAnalyze).toHaveBeenNthCalledWith(2, "alice");
  });

  it.each([["alice", "bob"], ["bob", "alice"]])("prevents late response overwrite for %s to %s target changes", async (firstTarget, secondTarget) => {
    const first = deferred<GitHubPortfolioInterpretationResponse>();
    const second = deferred<GitHubPortfolioInterpretationResponse>();
    mockedAnalyze.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    render(<AnalysisForm />);
    submit(firstTarget);
    submit(secondTarget);
    second.resolve(result(secondTarget));
    await waitFor(() => expect(screen.getByTestId("result-shell")).toHaveTextContent(secondTarget));
    first.resolve(result(firstTarget));
    await waitFor(() => expect(screen.getByTestId("result-shell")).toHaveTextContent(secondTarget));
  });
});
