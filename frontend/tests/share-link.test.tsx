import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisForm } from "../components/analysis-form";
import { CopyLinkButton } from "../components/copy-link-button";
import { userPageMetadata, userPath, usernameFromRouteParam } from "../lib/share";
import type { GitHubPortfolioInterpretationResponse } from "../lib/types";

const mockedAnalyze = vi.hoisted(() => vi.fn());
const mockedUseAuth = vi.hoisted(() => vi.fn());

vi.mock("../lib/api", () => ({
  analyzePortfolioWithInterpretation: mockedAnalyze,
  ApiError: class ApiError extends Error {},
}));
vi.mock("../components/auth-provider", () => ({ useAuth: mockedUseAuth }));
vi.mock("../components/analysis-result-shell", () => ({
  AnalysisResultShell: ({ result }: { result: GitHubPortfolioInterpretationResponse }) => <div data-testid="result-shell">{result.analysis.user.username}</div>,
}));

describe("shareable link helpers", () => {
  it("builds an encoded result path", () => {
    expect(userPath("octocat")).toBe("/u/octocat");
    expect(userPath("a-b")).toBe("/u/a-b");
  });

  it.each(["octocat", "Octo-Cat", "a", "a".repeat(39)])("accepts %s as a route segment", (raw) => {
    expect(usernameFromRouteParam(raw)).toBe(raw);
  });

  it.each([
    "",
    "-bad",
    "bad-",
    "bad--name",
    "bad%20name",
    "%40octocat",
    "%E0%A4%A",
    "a".repeat(40),
    "octocat%2Frepo",
    "octo%20cat",
    "%20octocat",
  ])("rejects %s", (raw) => {
    expect(usernameFromRouteParam(raw)).toBeNull();
  });

  it("decodes an encoded valid login", () => {
    expect(usernameFromRouteParam("octo%2Dcat")).toBe("octo-cat");
  });

  it("describes the page for search and social previews", () => {
    expect(userPageMetadata("octocat")).toEqual({
      title: "@octocat portföy analizi | DevLens",
      description: "@octocat için herkese açık GitHub kanıtlarına dayalı deterministik portföy skoru, repository bulguları ve gelişim alanları.",
      path: "/u/octocat",
    });
  });
});

describe("CopyLinkButton", () => {
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("copies the absolute shareable link and confirms it", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    render(<CopyLinkButton username="octocat" />);

    fireEvent.click(screen.getByRole("button", { name: /Bağlantıyı kopyala/ }));

    await waitFor(() => expect(screen.getByRole("button")).toHaveTextContent("Kopyalandı"));
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/u/octocat`);
    expect(screen.getByRole("status")).toHaveTextContent("Bağlantı panoya kopyalandı.");
  });

  it("returns to its idle label after a moment", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("navigator", { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
    render(<CopyLinkButton username="octocat" />);

    await act(async () => { fireEvent.click(screen.getByRole("button")); });
    expect(screen.getByRole("button")).toHaveTextContent("Kopyalandı");
    act(() => { vi.advanceTimersByTime(2600); });
    expect(screen.getByRole("button")).toHaveTextContent("Bağlantıyı kopyala");
  });

  it("reports a clipboard failure without pretending it worked", async () => {
    vi.stubGlobal("navigator", { clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) } });
    render(<CopyLinkButton username="octocat" />);

    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => expect(screen.getByRole("button")).toHaveTextContent("Kopyalanamadı"));
    expect(screen.getByRole("status")).toHaveTextContent("adres çubuğundaki bağlantıyı kullanabilirsiniz");
  });

  it("falls back to a hidden textarea when the clipboard permission is denied", async () => {
    vi.stubGlobal("navigator", { clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) } });
    const execCommand = vi.fn().mockReturnValue(true);
    Object.defineProperty(document, "execCommand", { value: execCommand, configurable: true });
    render(<CopyLinkButton username="octocat" />);

    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => expect(screen.getByRole("button")).toHaveTextContent("Kopyalandı"));
    expect(execCommand).toHaveBeenCalledWith("copy");
    expect(document.querySelector("textarea")).toBeNull();
    Reflect.deleteProperty(document, "execCommand");
  });

  it("also works when the clipboard API is missing entirely", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("navigator", {});
    render(<CopyLinkButton username="octocat" />);

    await user.click(screen.getByRole("button"));

    await waitFor(() => expect(screen.getByRole("button")).toHaveTextContent("Kopyalanamadı"));
  });
});

describe("AnalysisForm with a linked username", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
    mockedAnalyze.mockImplementation(async (username: string) => ({ analysis: { user: { username } } }));
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    window.history.replaceState(null, "", "/");
  });

  it("starts the analysis by itself once the session state is known, exactly once", async () => {
    mockedUseAuth.mockReturnValue({ status: "anonymous", user: null });
    const { rerender } = render(<AnalysisForm initialUsername="octocat" />);

    await waitFor(() => expect(screen.getByTestId("result-shell")).toHaveTextContent("octocat"));
    expect(mockedAnalyze).toHaveBeenCalledTimes(1);
    expect(mockedAnalyze).toHaveBeenCalledWith("octocat", expect.anything());
    expect((screen.getByLabelText("GitHub kullanıcı adı") as HTMLInputElement).value).toBe("octocat");

    rerender(<AnalysisForm initialUsername="octocat" />);
    expect(mockedAnalyze).toHaveBeenCalledTimes(1);
  });

  it("waits while the session is still loading so the identity reset cannot cancel the request", async () => {
    mockedUseAuth.mockReturnValue({ status: "loading", user: null });
    const { rerender } = render(<AnalysisForm initialUsername="octocat" />);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(mockedAnalyze).not.toHaveBeenCalled();

    mockedUseAuth.mockReturnValue({ status: "anonymous", user: null });
    rerender(<AnalysisForm initialUsername="octocat" />);

    await waitFor(() => expect(mockedAnalyze).toHaveBeenCalledTimes(1));
  });

  it("does not start anything without a linked username", async () => {
    mockedUseAuth.mockReturnValue({ status: "anonymous", user: null });
    render(<AnalysisForm />);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(mockedAnalyze).not.toHaveBeenCalled();
  });

  it("moves the address bar to the shareable link of the shown result", async () => {
    mockedUseAuth.mockReturnValue({ status: "anonymous", user: null });
    render(<AnalysisForm />);

    fireEvent.change(screen.getByLabelText("GitHub kullanıcı adı"), { target: { value: "https://github.com/Torvalds" } });
    fireEvent.submit(screen.getByLabelText("GitHub kullanıcı adı").closest("form")!);

    await waitFor(() => expect(screen.getByTestId("result-shell")).toBeInTheDocument());
    expect(window.location.pathname).toBe("/u/Torvalds");
  });

  it("leaves the address alone when the analysis fails", async () => {
    mockedUseAuth.mockReturnValue({ status: "anonymous", user: null });
    mockedAnalyze.mockRejectedValue(new Error("boom"));
    render(<AnalysisForm />);

    fireEvent.change(screen.getByLabelText("GitHub kullanıcı adı"), { target: { value: "octocat" } });
    fireEvent.submit(screen.getByLabelText("GitHub kullanıcı adı").closest("form")!);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(window.location.pathname).toBe("/");
  });
});
