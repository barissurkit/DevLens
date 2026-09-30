import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { RepositoryAnalysisSection } from "../components/repository-analysis-section";
import type { PortfolioRepositoryResult } from "../lib/types";

function makeResult(name: string, overall: number, isPartial = false, category = "Backend"): PortfolioRepositoryResult {
  const repository = {
    name, description: null, html_url: `https://github.com/demo/${name}`, primary_language: null,
    stars: 0, forks: 0, topics: [], created_at: "", updated_at: "", archived: false, fork: false, default_branch: "main",
  };
  return {
    repository,
    score: { version: "1", overall_score: overall, dimensions: [], is_partial: isPartial, limitations: [] },
    analysis: {
      repository,
      readme: { exists: true, content_length: 1, has_title: true, has_description: true, has_installation: false, has_usage: false, has_technologies: false, has_requirements: false, has_images: false, has_demo_link: false },
      structure: { has_tests: false, has_ci: false, has_dockerfile: false, has_compose: false, has_env_example: false, has_license: false, has_gitignore: false, has_contributing: false },
      tree_truncated: isPartial,
      technologies: { dependencies: [], technologies: [] },
      classification: { categories: [], primary_category: category },
    },
  };
}

const repositories = [makeResult("bravo", 80), makeResult("alpha", 30, true), makeResult("charlie", 60)];

function renderedNames() {
  return Array.from(document.querySelectorAll("details summary span.break-words")).map((node) => node.textContent);
}

describe("RepositoryAnalysisSection sıralama ve filtreleme", () => {
  afterEach(cleanup);

  it("varsayılan sırayı korur ve skora göre sıralar", async () => {
    const user = userEvent.setup();
    render(<RepositoryAnalysisSection repositories={repositories} failures={[]} excluded={[]} />);
    expect(renderedNames()).toEqual(["bravo", "alpha", "charlie"]);

    await user.selectOptions(screen.getByRole("combobox"), "score_asc");
    expect(renderedNames()).toEqual(["alpha", "charlie", "bravo"]);

    await user.selectOptions(screen.getByRole("combobox"), "score_desc");
    expect(renderedNames()).toEqual(["bravo", "charlie", "alpha"]);

    await user.selectOptions(screen.getByRole("combobox"), "name");
    expect(renderedNames()).toEqual(["alpha", "bravo", "charlie"]);
  });

  it("kısmi kanıt ve düşük skor filtrelerini uygular", async () => {
    const user = userEvent.setup();
    render(<RepositoryAnalysisSection repositories={repositories} failures={[]} excluded={[]} />);
    const controls = screen.getByRole("group", { name: /sıralama ve filtreleme/i });

    await user.click(within(controls).getByLabelText(/kısmi kanıtlı/i));
    expect(renderedNames()).toEqual(["alpha"]);
    expect(screen.getByText("1 / 3 repository gösteriliyor")).toBeInTheDocument();

    await user.click(within(controls).getByLabelText(/kısmi kanıtlı/i));
    await user.click(within(controls).getByLabelText(/düşük skorlu/i));
    expect(renderedNames()).toEqual(["alpha"]);
  });

  it("filtre sonuç vermediğinde boş durum mesajı gösterir", async () => {
    const user = userEvent.setup();
    render(<RepositoryAnalysisSection repositories={[makeResult("bravo", 80), makeResult("charlie", 60)]} failures={[]} excluded={[]} />);
    await user.click(screen.getByLabelText(/düşük skorlu/i));
    expect(screen.getByText("Seçilen filtrelerle eşleşen repository yok.")).toBeInTheDocument();
  });

  it("tek repository varsa kontrolleri göstermez", () => {
    render(<RepositoryAnalysisSection repositories={[makeResult("bravo", 80)]} failures={[]} excluded={[]} />);
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("kategori adını Türkçe etiketle gösterir", () => {
    render(<RepositoryAnalysisSection repositories={[makeResult("ml-repo", 70, false, "Machine Learning")]} failures={[]} excluded={[]} />);
    expect(screen.getByText("Makine Öğrenmesi")).toBeInTheDocument();
    expect(screen.queryByText("Machine Learning")).not.toBeInTheDocument();
  });
});
