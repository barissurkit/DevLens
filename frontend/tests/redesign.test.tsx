import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisForm } from "../components/analysis-form";
import { FeatureStrip, HeroCopy, SamplePreview } from "../components/landing-content";
import { SiteShell } from "../components/site-shell";
import NotFound from "../app/not-found";

const mockedAnalyze = vi.hoisted(() => vi.fn());
const mockedUseAuth = vi.hoisted(() => vi.fn());

vi.mock("../lib/api", () => ({
  analyzePortfolioWithInterpretation: mockedAnalyze,
  getAuthStartUrl: () => "http://localhost:8000/api/v1/auth/github",
  ApiError: class ApiError extends Error {
    constructor(message: string, readonly status: number, readonly code: string) {
      super(message);
    }
  },
}));
vi.mock("../components/auth-provider", () => ({ useAuth: mockedUseAuth }));

beforeEach(() => mockedUseAuth.mockReturnValue({ status: "anonymous", user: null, errorMessage: null, refresh: vi.fn(), logout: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("site chrome", () => {
  it("offers a skip link, primary navigation and footer navigation", () => {
    render(<SiteShell><p>içerik</p></SiteShell>);

    expect(screen.getByRole("link", { name: "Ana içeriğe geç" })).toHaveAttribute("href", "#main-content");
    const primary = screen.getByRole("navigation", { name: "Ana gezinme" });
    expect(within(primary).getAllByRole("link").map((link) => link.getAttribute("href"))).toEqual(["/#nasil-calisir", "/#puanlama", "/#sss"]);
    expect(screen.getByRole("navigation", { name: "Ürün" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Kaynaklar" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
  });
});

describe("landing content", () => {
  it("explains how it works, how scoring works and answers common questions", () => {
    render(<><HeroCopy /><SamplePreview /><FeatureStrip /></>);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("GitHub portföyündeki kanıtları daha net gör.");
    expect(screen.getByRole("heading", { name: "Nasıl çalışır?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Şeffaf puanlama" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sık sorulan sorular" })).toBeInTheDocument();
    // The section anchors that the header and footer link to.
    for (const id of ["nasil-calisir", "puanlama", "sss"]) expect(document.getElementById(id)).not.toBeNull();
    // Scoring weights shown on the page match the backend's 50/30/20 split.
    expect(screen.getByText("50 puan")).toBeInTheDocument();
    expect(screen.getByText("30 puan")).toBeInTheDocument();
    expect(screen.getByText("20 puan")).toBeInTheDocument();
  });

  it("keeps every FAQ answer reachable through a native disclosure", () => {
    render(<FeatureStrip />);

    const questions = screen.getAllByText(/\?$/, { selector: "summary" });
    expect(questions).toHaveLength(5);
    for (const question of questions) expect(question.closest("details")).not.toBeNull();
  });
});

describe("linked result page", () => {
  it("shows a compact search bar and a skeleton, not the marketing hero, while loading", async () => {
    mockedAnalyze.mockReturnValue(new Promise(() => undefined));
    render(<AnalysisForm initialUsername="octocat" hero={<HeroCopy />} preview={<SamplePreview />} features={<FeatureStrip />} />);

    await waitFor(() => expect(mockedAnalyze).toHaveBeenCalled());
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    expect(screen.queryByText("Nasıl çalışır?")).toBeNull();
    expect(document.querySelector(".skeleton")).not.toBeNull();
    // The field keeps its accessible name even though its label is visually hidden.
    expect(screen.getByLabelText("GitHub kullanıcı adı")).toHaveValue("octocat");
  });

  it("brings the landing content back when the linked analysis fails", async () => {
    const { ApiError } = await import("../lib/api");
    mockedAnalyze.mockRejectedValue(new ApiError("yok", 404, "github_user_not_found"));
    render(<AnalysisForm initialUsername="ghost" hero={<HeroCopy />} preview={<SamplePreview />} features={<FeatureStrip />} />);

    await waitFor(() => expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument());
    expect(document.querySelector(".skeleton")).toBeNull();
  });
});

describe("not found page", () => {
  it("points back to the home page", () => {
    render(<NotFound />);

    expect(screen.getByRole("heading", { name: "Aradığın sayfa bulunamadı" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ana sayfaya dön" })).toHaveAttribute("href", "/");
  });
});

describe("search shortcut", () => {
  it("focuses the search field on '/' but not while typing elsewhere", async () => {
    const { fireEvent } = await import("@testing-library/react");
    render(<><AnalysisForm /><textarea aria-label="not" /></>);
    const input = screen.getByLabelText("GitHub kullanıcı adı");

    fireEvent.keyDown(document.body, { key: "/" });
    expect(input).toHaveFocus();

    const other = screen.getByLabelText("not");
    other.focus();
    fireEvent.keyDown(other, { key: "/" });
    expect(other).toHaveFocus();
  });
});

describe("failed sign-in notice", () => {
  afterEach(() => window.history.replaceState(null, "", "/"));

  it("explains a failed login and cleans the address", async () => {
    window.history.replaceState(null, "", "/?auth_error=authentication_failed");
    render(<SiteShell><p>içerik</p></SiteShell>);

    expect(await screen.findByRole("alert")).toHaveTextContent("GitHub ile giriş tamamlanamadı");
    expect(window.location.search).toBe("");
  });

  it("can be dismissed and stays quiet without the parameter", async () => {
    const { fireEvent } = await import("@testing-library/react");
    window.history.replaceState(null, "", "/?auth_error=whatever");
    const { unmount } = render(<SiteShell><p>içerik</p></SiteShell>);
    expect(await screen.findByRole("alert")).toHaveTextContent("Giriş sırasında bir sorun oluştu");
    fireEvent.click(screen.getByRole("button", { name: "Kapat" }));
    expect(screen.queryByRole("alert")).toBeNull();
    unmount();

    render(<SiteShell><p>içerik</p></SiteShell>);
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("signal labels", () => {
  it("names known signals in Turkish and leaves unknown keys untouched", async () => {
    const { signalLabel } = await import("../lib/signals");
    expect(signalLabel("ci_workflow")).toBe("CI iş akışı");
    expect(signalLabel("readme_usage")).toBe("README kullanım bölümü");
    expect(signalLabel("something_new")).toBe("something_new");
  });
});

describe("unknown GitHub users", () => {
  it("are marked noindex while the not-found error is shown", async () => {
    const { ApiError } = await import("../lib/api");
    mockedAnalyze.mockRejectedValue(new ApiError("yok", 404, "github_user_not_found"));
    const { unmount } = render(<AnalysisForm initialUsername="ghost" />);

    await waitFor(() => expect(document.querySelector('meta[name="robots"][content="noindex"]')).not.toBeNull());
    unmount();
    expect(document.querySelector('meta[name="robots"]')).toBeNull();
  });
});

describe("result tab warning", () => {
  it("marks a tab that currently has nothing to show", async () => {
    const { ResultTabs } = await import("../components/result-tabs");
    render(<ResultTabs idPrefix="t" activeId="a" onChange={() => undefined} tabs={[{ id: "a", label: "Bir" }, { id: "ai", label: "AI Yorumu", warning: "şu anda kullanılamıyor" }]} />);

    expect(screen.getByRole("tab", { name: /AI Yorumu/ })).toHaveTextContent("(şu anda kullanılamıyor)");
    expect(screen.getByRole("tab", { name: "Bir" })).not.toHaveTextContent("(");
  });
});
