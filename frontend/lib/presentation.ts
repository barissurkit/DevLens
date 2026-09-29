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

export interface ScoreTone {
  label: string;
  text: string;
  stroke: string;
  badge: string;
}

export function scoreTone(score: number): ScoreTone {
  if (score >= 75) return { label: "Güçlü", text: "text-emerald-700", stroke: "stroke-emerald-500", badge: "bg-emerald-50 text-emerald-800" };
  if (score >= 50) return { label: "Gelişebilir", text: "text-amber-700", stroke: "stroke-amber-500", badge: "bg-amber-50 text-amber-800" };
  return { label: "Zayıf", text: "text-rose-700", stroke: "stroke-rose-500", badge: "bg-rose-50 text-rose-800" };
}

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

export function portfolioModeLabel(viewerContext: ViewerContext): string {
  return viewerContext.mode === "my_workspace" ? "Senin portföyün" : "Herkese açık portföy görüntüleniyor";
}
import type { ViewerContext } from "./types";
