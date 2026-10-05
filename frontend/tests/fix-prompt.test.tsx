import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FixPromptSection } from "../components/fix-prompt-section";
import { buildFixPrompt } from "../lib/fix-prompt";
import { topImprovements } from "../lib/priorities";
import { SCORING_GUIDE } from "../lib/scoring-guide";
import type { GitHubPortfolioAnalysis } from "../lib/types";

const copyTextMock = vi.hoisted(() => vi.fn());
vi.mock("../lib/share", async (importOriginal) => ({ ...(await importOriginal<typeof import("../lib/share")>()), copyText: copyTextMock }));

/** A recorded analysis (8 repositories, score 44) scored by the backend. */
const analysis = JSON.parse(readFileSync(resolve(__dirname, "../e2e/fixtures/portfolio.json"), "utf-8")).analysis as GitHubPortfolioAnalysis;

beforeEach(() => copyTextMock.mockResolvedValue(true));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("buildFixPrompt", () => {
  const prompt = buildFixPrompt(analysis) as string;

  it("states who the portfolio belongs to and where it stands", () => {
    expect(prompt).toContain(`Ben @${analysis.user.username}`);
    expect(prompt).toContain(`Portföy skoru: ${analysis.score.overall_score} / 100`);
    for (const dimension of SCORING_GUIDE) expect(prompt).toContain(dimension.label);
  });

  it("lists every gap in the order of the points it would add", () => {
    const expected = topImprovements(analysis.score.dimensions, 100);
    const headings = [...prompt.matchAll(/^### \d+\. (.+?) \(\+/gm)].map((match) => match[1]);

    expect(headings).toEqual(expected.map((item) => item.label));
    expect(headings.length).toBeGreaterThan(3);
  });

  it("names the repositories a rule is missing in, with their links", () => {
    const section = prompt.split("### 1. ")[1].split("### 2. ")[0];

    expect(section).toContain("Eksik olan repository'ler:");
    expect(section).toMatch(new RegExp(`- ${analysis.user.username}/\\S+: https://github\\.com/`));
  });

  it("keeps the agent honest: separate pull requests, no invented content, no licence choice", () => {
    expect(prompt).toContain("ayrı bir pull request");
    expect(prompt).toContain("İçeriği uydurma");
    expect(prompt).toContain("lisans seçme");
    expect(prompt).toContain("Gizli bilgi");
  });

  it("is null without a score or when nothing is left to improve", () => {
    expect(buildFixPrompt({ ...analysis, score: { ...analysis.score, is_available: false, overall_score: null } })).toBeNull();
    const complete = {
      ...analysis,
      score: {
        ...analysis.score,
        dimensions: analysis.score.dimensions.map((dimension) => ({
          ...dimension,
          rules: dimension.rules.map((rule) => ({ ...rule, detected_repository_count: rule.analyzed_repository_count })),
        })),
      },
    };
    expect(buildFixPrompt(complete)).toBeNull();
  });

  it("lists at most twelve repositories per rule and counts the rest", () => {
    const base = analysis.repository_analysis.repositories[0];
    const many = Array.from({ length: 20 }, (_, index) => ({
      ...base,
      repository: { ...base.repository, name: `repo-${index}`, html_url: `https://github.com/x/repo-${index}` },
      analysis: { ...base.analysis, structure: { ...base.analysis.structure, has_tests: false } },
    }));
    const wide = {
      ...analysis,
      repository_analysis: { ...analysis.repository_analysis, repositories: many },
      score: {
        ...analysis.score,
        dimensions: analysis.score.dimensions.map((dimension) => ({
          ...dimension,
          rules: dimension.rules.map((rule) => (rule.key === "tests_structure" ? { ...rule, detected_repository_count: 0, analyzed_repository_count: 20 } : rule)),
        })),
      },
    };

    const text = buildFixPrompt(wide) as string;
    const section = text.split("### 1. ")[1].split("### 2. ")[0];

    expect(section).toContain("Test Yapısı");
    expect(section.match(/- barissurkit\/repo-/g)).toHaveLength(12);
    expect(section).toContain("… ve 8 repository daha");
  });
});

describe("FixPromptSection", () => {
  it("keeps the prompt collapsed, shows it on request and copies the whole text", async () => {
    const user = userEvent.setup();
    render(<FixPromptSection analysis={analysis} />);

    expect(screen.getByRole("heading", { name: "Yapay zekâ ile düzelt" })).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();

    await user.click(screen.getByRole("button", { name: "İstemi göster" }));
    const text = screen.getByRole("textbox", { name: "Yapay zekâ için düzeltme istemi" });
    expect(text).toHaveAttribute("readonly");
    expect((text as HTMLTextAreaElement).value).toBe(buildFixPrompt(analysis));

    await user.click(screen.getByRole("button", { name: "İstemi kopyala" }));
    expect(copyTextMock).toHaveBeenCalledWith(buildFixPrompt(analysis));
    expect(await screen.findByRole("button", { name: "Kopyalandı" })).toBeInTheDocument();
  });

  it("says so when copying is not possible", async () => {
    copyTextMock.mockResolvedValue(false);
    const user = userEvent.setup();
    render(<FixPromptSection analysis={analysis} />);

    await user.click(screen.getByRole("button", { name: "İstemi kopyala" }));

    expect(await screen.findByRole("button", { name: "Kopyalanamadı" })).toBeInTheDocument();
  });

  it("renders nothing when there is nothing to fix", () => {
    const { container } = render(<FixPromptSection analysis={{ ...analysis, score: { ...analysis.score, is_available: false, overall_score: null } }} />);

    expect(container).toBeEmptyDOMElement();
  });
});
