const CATEGORY_LABELS: Record<string, string> = {
  "Machine Learning": "Makine Öğrenmesi",
  "Data Science": "Veri Bilimi",
  Backend: "Backend",
  Frontend: "Frontend",
  "Full Stack": "Full Stack",
  DevOps: "DevOps",
  "Data Engineering": "Veri Mühendisliği",
  "CLI / Developer Tool": "CLI / Geliştirici Aracı",
  "Learning / Experiment": "Öğrenme / Deney",
  Other: "Diğer",
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

export function portfolioModeLabel(viewerContext: ViewerContext): string {
  return viewerContext.mode === "my_workspace" ? "Your Portfolio" : "Viewing public portfolio";
}
import type { ViewerContext } from "./types";
