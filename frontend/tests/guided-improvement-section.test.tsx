import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GuidedImprovementSection } from "../components/guided-improvement-section";

const item = {
  rule_key: "readme_exists",
  title: "README dosyanı güçlendir",
  why: "Kullanıcıların projeyi anlamasına yardımcı olur.",
  steps: ["README dosyasını ekle.", "Kullanım örneği ekle."],
  verification: { detected_repository_count: 2, analyzed_repository_count: 2, current_state: "needs_improvement" as const, analysis_available: true, analysis_partial: false, reanalysis_required: true },
};

afterEach(cleanup);

describe("Guided Improvement section", () => {
  it("renders Turkish guidance, verification, and the shared re-analysis action", async () => {
    const onReanalyze = vi.fn();
    const user = userEvent.setup();
    render(<GuidedImprovementSection improvements={[item]} onReanalyze={onReanalyze} />);
    expect(screen.getByRole("heading", { name: "Guided Improvement" })).toBeInTheDocument();
    expect(screen.getByText(item.why)).toBeInTheDocument();
    expect(screen.getByText(item.steps[0])).toBeInTheDocument();
    expect(screen.getByText(/2 repository tespit edildi/)).toBeInTheDocument();
    expect(screen.getByText(/İyileştirme gerekiyor/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tekrar analiz et" }));
    expect(onReanalyze).toHaveBeenCalledOnce();
  });

  it("does not render an empty guidance section", () => {
    render(<GuidedImprovementSection improvements={[]} onReanalyze={vi.fn()} />);
    expect(screen.queryByRole("heading", { name: "Guided Improvement" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Tüm kontrolleri geçtin|tamamen doğrulandı/i)).not.toBeInTheDocument();
  });
});
