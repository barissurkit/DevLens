import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { BrandMark, BrandWordmark } from "../components/brand-mark";
import { PrintCover } from "../components/print-cover";
import { BRAND_SVG, BRAND_SVG_DATA_URI } from "../lib/brand-svg";
import type { GitHubPortfolioAnalysis } from "../lib/types";

afterEach(cleanup);

function analysis(overall: number | null, name: string | null = "Ada Lovelace"): GitHubPortfolioAnalysis {
  return {
    user: { username: "ada", name },
    score: {
      version: "v3",
      is_available: overall !== null,
      overall_score: overall,
      scored_repository_count: 5,
      is_partial: false,
      limitations: [],
      dimensions: overall === null ? [] : [
        { key: "documentation_consistency", label: "Dokümantasyon Tutarlılığı", points_earned: 30, points_possible: 40, score: 75, rules: [] },
        { key: "maintenance_visibility", label: "Bakım ve Görünürlük", points_earned: 10, points_possible: 20, score: 50, rules: [] },
      ],
    },
  } as unknown as GitHubPortfolioAnalysis;
}

describe("brand", () => {
  it("draws a decorative mark whose gradient ids follow the given prefix", () => {
    const { container } = render(<><BrandMark idPrefix="one" /><BrandMark idPrefix="two" /></>);

    const ids = [...container.querySelectorAll("linearGradient")].map((node) => node.id);
    expect(ids).toEqual(["one-tile", "one-sheen", "two-tile", "two-sheen"]);
    expect(new Set(ids).size).toBe(4);
    for (const svg of container.querySelectorAll("svg")) expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("keeps the product name readable as one word", () => {
    render(<BrandWordmark />);

    expect(screen.getByText(/Dev/)).toHaveTextContent("DevLens");
  });

  it("offers the same mark as a standalone SVG for the favicon-style uses", () => {
    expect(BRAND_SVG.startsWith("<svg ")).toBe(true);
    expect(BRAND_SVG).toContain('viewBox="0 0 48 48"');
    expect(decodeURIComponent(BRAND_SVG_DATA_URI.replace("data:image/svg+xml;utf8,", ""))).toBe(BRAND_SVG);
  });
});

describe("printed cover", () => {
  it("shows the report title, the person, the score band, every dimension and the source", () => {
    render(<PrintCover analysis={analysis(62)} generatedAt="2026-10-04T12:30:00Z" url="https://devlens.example/u/ada" />);

    expect(screen.getByText("Portföy Analiz Raporu")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, hidden: true })).toHaveTextContent("Ada Lovelace");
    expect(screen.getByText("@ada")).toBeInTheDocument();
    expect(screen.getByText("Gelişebilir")).toBeInTheDocument();
    expect(screen.getByText("Dokümantasyon Tutarlılığı")).toBeInTheDocument();
    expect(screen.getByText("30 / 40")).toBeInTheDocument();
    expect(screen.getByText("10 / 20")).toBeInTheDocument();
    expect(screen.getByText("https://devlens.example/u/ada")).toBeInTheDocument();
    expect(screen.getByText(/4 Ekim 2026/)).toBeInTheDocument();
  });

  it("is hidden from screens and assistive technology and is only laid out for print", () => {
    const { container } = render(<PrintCover analysis={analysis(62)} url="https://devlens.example/u/ada" />);

    const cover = container.querySelector(".print-cover");
    expect(cover).toHaveAttribute("aria-hidden", "true");
    expect(cover?.className).toContain("hidden");
    expect(cover?.className).toContain("print:flex");
  });

  it("falls back to the login when the profile has no name, and omits the score when there is none", () => {
    render(<PrintCover analysis={analysis(null, null)} url="https://devlens.example/u/ada" />);

    expect(screen.getByRole("heading", { level: 1, hidden: true })).toHaveTextContent("@ada");
    expect(screen.queryByText(/\/ 100/)).toBeNull();
    expect(screen.queryByRole("list", { hidden: true })).toBeNull();
  });
});
