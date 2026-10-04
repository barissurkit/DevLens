import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import fixture from "../e2e/fixtures/portfolio.json";
import { ReportMenu, reportPath } from "../components/report/report-menu";
import { buildReportBlocks, SECTION_TITLES } from "../components/report/report-blocks";
import { buildReportModel, overviewSentence, parseReportMode } from "../lib/report";
import type { GitHubPortfolioAnalysis } from "../lib/types";

const analysis = fixture.analysis as unknown as GitHubPortfolioAnalysis;

afterEach(cleanup);

describe("report model", () => {
  it("reads the mode from the address and falls back to the summary", () => {
    expect(parseReportMode("detay")).toBe("detay");
    expect(parseReportMode("ozet")).toBe("ozet");
    for (const value of [null, undefined, "", "x", "DETAY"]) expect(parseReportMode(value)).toBe("ozet");
  });

  it("builds the summary without repository details", () => {
    const model = buildReportModel(analysis, "ozet");

    expect(model.repositories).toEqual([]);
    expect(model.username).toBe("barissurkit");
    expect(model.hasScore).toBe(true);
    expect(model.dimensions.map((dimension) => dimension.key)).toEqual(["documentation_consistency", "testing_automation_adoption", "repository_hygiene_consistency", "maintenance_visibility"]);
    expect(model.dimensions.reduce((sum, dimension) => sum + dimension.possible, 0)).toBe(100);
    expect(model.dimensions.reduce((sum, dimension) => sum + dimension.earned, 0)).toBe(model.score);
  });

  it("builds the detailed report with every analyzed repository, best score first", () => {
    const model = buildReportModel(analysis, "detay");
    const scores = model.repositories.map((repository) => repository.score);

    expect(model.repositories).toHaveLength(analysis.repository_analysis.repositories.length);
    expect(scores).toEqual([...scores].sort((a, b) => b - a));
    for (const repository of model.repositories) {
      expect(repository.groups.map((group) => group.title)).toEqual(["Dokümantasyon", "Yapı ve otomasyon", "Bakım ve görünürlük"]);
      expect(repository.groups.flatMap((group) => group.checks)).toHaveLength(15);
    }
  });

  it("limits the priorities and never promises more points than are left", () => {
    const model = buildReportModel(analysis, "ozet");

    expect(model.priorities.length).toBeLessThanOrEqual(3);
    expect(model.potentialGain).toBeLessThanOrEqual(100 - (model.score as number));
    expect(model.strengths.length).toBeLessThanOrEqual(3);
  });

  it("describes the portfolio in one sentence built from its numbers", () => {
    const sentence = overviewSentence(analysis);

    expect(sentence).toContain("@barissurkit");
    expect(sentence).toContain("44 / 100");
    expect(sentence).toMatch(/En güçlü boyut %\d+ ile ".+", en zayıf boyut %\d+ ile ".+" oldu\./);
  });

  it("says why there is no score when too few repositories were analyzed", () => {
    const small = { ...analysis, score: { ...analysis.score, is_available: false, overall_score: null, dimensions: [] } } as GitHubPortfolioAnalysis;

    const model = buildReportModel(small, "ozet");

    expect(model.hasScore).toBe(false);
    expect(model.score).toBeNull();
    expect(model.tone).toBeNull();
    expect(overviewSentence(small)).toContain("en az iki repository");
  });
});

describe("report blocks", () => {
  it("opens every section with a title block and keeps its blocks in that section", () => {
    const blocks = buildReportBlocks(buildReportModel(analysis, "detay"));
    const titles = blocks.filter((block) => block.isSectionTitle);

    expect(titles.length).toBeGreaterThan(5);
    for (const title of titles) {
      expect(title.keepWithNext).toBe(true);
      expect(SECTION_TITLES[title.section as string]).toBeTruthy();
    }
    expect(blocks[0].isSectionTitle).toBe(true);
    for (const block of blocks) expect(block.section).toBeTruthy();
    expect(new Set(blocks.map((block) => block.key)).size).toBe(blocks.length);
  });

  it("starts the repository and method sections on new pages in the detailed report only", () => {
    const detailed = buildReportBlocks(buildReportModel(analysis, "detay"));
    const summary = buildReportBlocks(buildReportModel(analysis, "ozet"));

    expect(detailed.filter((block) => block.breakBefore).map((block) => block.key)).toEqual(["title-repositories", "title-method"]);
    expect(summary.some((block) => block.breakBefore)).toBe(false);
    expect(summary.some((block) => block.section === "repositories" || block.section === "method")).toBe(false);
  });
});

describe("ReportMenu", () => {
  it("opens two report links and closes with Escape", () => {
    render(<ReportMenu username="octocat" />);
    const button = screen.getByRole("button", { name: /Yazdır \/ PDF/ });
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("group", { name: "Rapor türü" })).toBeNull();

    fireEvent.click(button);

    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: /Özet rapor/ })).toHaveAttribute("href", reportPath("octocat", "ozet"));
    expect(screen.getByRole("link", { name: /Ayrıntılı rapor/ })).toHaveAttribute("href", "/u/octocat/rapor?tur=detay");

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("group", { name: "Rapor türü" })).toBeNull();
    expect(button).toHaveFocus();
  });

  it("closes when the user clicks elsewhere and toggles with the button", () => {
    render(<><ReportMenu username="octocat" /><p>başka bir yer</p></>);
    const button = screen.getByRole("button", { name: /Yazdır \/ PDF/ });

    fireEvent.click(button);
    fireEvent.pointerDown(screen.getByText("başka bir yer"));
    expect(screen.queryByRole("group", { name: "Rapor türü" })).toBeNull();

    fireEvent.click(button);
    expect(screen.getByRole("group", { name: "Rapor türü" })).toBeInTheDocument();
    fireEvent.click(button);
    expect(screen.queryByRole("group", { name: "Rapor türü" })).toBeNull();
  });
});
