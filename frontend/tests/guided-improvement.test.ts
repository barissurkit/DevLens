import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { analyzePortfolio, analyzePortfolioWithInterpretation } from "../lib/api";

const analysis = { user: {}, selection: {}, repository_analysis: {}, aggregation: {}, intelligence: {}, score: {} };
const viewerContext = { is_owner: true, mode: "my_workspace" };
const validItem = {
  rule_key: "readme_exists",
  title: "README dosyanı güçlendir",
  why: "Kullanıcıların projeyi anlamasına yardımcı olur.",
  steps: ["README dosyasını ekle."],
  verification: {
    detected_repository_count: 2,
    analyzed_repository_count: 2,
    current_state: "needs_improvement",
    analysis_available: true,
    analysis_partial: false,
    reanalysis_required: true,
  },
};
const interpretation = {
  status: "unavailable",
  reason: "not_configured",
};

describe("Guided Improvement response validation", () => {
  beforeEach(() => vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000"));
  afterEach(() => { vi.unstubAllEnvs(); vi.restoreAllMocks(); });

  it("normalizes a missing guided_improvements field for old backend responses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ...analysis, viewer_context: viewerContext }), { status: 200 }));
    await expect(analyzePortfolio("alice")).resolves.toMatchObject({ guided_improvements: [] });
  });

  it("accepts valid guidance and normalizes missing guidance on interpretation responses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ analysis, interpretation, viewer_context: viewerContext }), { status: 200 }));
    await expect(analyzePortfolioWithInterpretation("alice")).resolves.toMatchObject({ guided_improvements: [] });

    vi.restoreAllMocks();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ analysis, interpretation, viewer_context: viewerContext, guided_improvements: [validItem] }), { status: 200 }));
    await expect(analyzePortfolioWithInterpretation("alice")).resolves.toMatchObject({ guided_improvements: [validItem] });
  });

  it.each([
    ["unknown state", { ...validItem, verification: { ...validItem.verification, current_state: "verified" } }],
    ["negative count", { ...validItem, verification: { ...validItem.verification, detected_repository_count: -1 } }],
    ["non-integer count", { ...validItem, verification: { ...validItem.verification, analyzed_repository_count: 1.5 } }],
    ["empty steps", { ...validItem, steps: [] }],
    ["empty step", { ...validItem, steps: [" "] }],
  ])("rejects malformed guidance: %s", async (_, item) => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ analysis, interpretation, viewer_context: viewerContext, guided_improvements: [item] }), { status: 200 }));
    await expect(analyzePortfolioWithInterpretation("alice")).rejects.toMatchObject({ code: "malformed_response" });
  });
});
