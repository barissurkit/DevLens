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
  /** Solid background for bars. */
  fill: string;
  badge: string;
}

/** Lower bounds of the score bands shown next to the portfolio score. */
export const SCORE_STRONG_MIN = 75;
export const SCORE_MODERATE_MIN = 50;

export function scoreTone(score: number): ScoreTone {
  if (score >= SCORE_STRONG_MIN) return { label: "Güçlü", text: "text-emerald-700", stroke: "stroke-emerald-500", fill: "bg-emerald-500", badge: "bg-emerald-50 text-emerald-800" };
  if (score >= SCORE_MODERATE_MIN) return { label: "Gelişebilir", text: "text-amber-700", stroke: "stroke-amber-500", fill: "bg-amber-500", badge: "bg-amber-50 text-amber-800" };
  return { label: "Zayıf", text: "text-rose-700", stroke: "stroke-rose-500", fill: "bg-rose-500", badge: "bg-rose-50 text-rose-800" };
}

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

export function portfolioModeLabel(viewerContext: ViewerContext): string {
  return viewerContext.mode === "my_workspace" ? "Senin portföyün" : "Herkese açık portföy görüntüleniyor";
}
import type { ViewerContext } from "./types";
