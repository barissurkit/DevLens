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
  ApiError: class ApiError extends Error {},
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
