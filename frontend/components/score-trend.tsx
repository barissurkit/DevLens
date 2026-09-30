import type { HistoryRecord } from "../lib/types";

interface ScoreTrendProps {
  history: HistoryRecord[];
}

const WIDTH = 320;
const HEIGHT = 96;
const PADDING_X = 12;
const PADDING_TOP = 10;
const PADDING_BOTTOM = 14;

const dateFormatter = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "short", timeZone: "Europe/Istanbul" });

interface Point {
  score: number;
  capturedAt: string;
}

/** Chronological (oldest first) points that have a score; earlier analyses without one are skipped. */
export function scorePoints(history: HistoryRecord[]): Point[] {
  return history
    .filter((record): record is HistoryRecord & { portfolio_score: number } => record.portfolio_score !== null)
    .map((record) => ({ score: record.portfolio_score, capturedAt: record.captured_at }))
    .sort((left, right) => Date.parse(left.capturedAt) - Date.parse(right.capturedAt));
}

/** A small accessible line chart of the portfolio score over time on a fixed 0-100 scale. */
export function ScoreTrend({ history }: ScoreTrendProps) {
  const points = scorePoints(history);
  if (points.length < 2) return null;

  const innerWidth = WIDTH - PADDING_X * 2;
  const innerHeight = HEIGHT - PADDING_TOP - PADDING_BOTTOM;
  const x = (index: number) => PADDING_X + (innerWidth * index) / (points.length - 1);
  const y = (score: number) => PADDING_TOP + innerHeight * (1 - Math.min(100, Math.max(0, score)) / 100);
  const coordinates = points.map((point, index) => `${x(index).toFixed(1)},${y(point.score).toFixed(1)}`);
  const first = points[0];
  const last = points[points.length - 1];
  const change = last.score - first.score;
  const summary = `Skor geçmişi, en eskiden en yeniye: ${points.map((point) => point.score).join(", ")}. ` +
    `${change === 0 ? "Değişmedi" : change > 0 ? `${change} puan arttı` : `${Math.abs(change)} puan azaldı`}.`;
  const tone = change > 0 ? "text-emerald-700" : change < 0 ? "text-rose-700" : "text-slate-600";

  return (
    <figure className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <figcaption className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Skor eğilimi</figcaption>
        <span className={`text-sm font-semibold ${tone}`}>
          {change === 0 ? "Değişmedi" : `${change > 0 ? "+" : "−"}${Math.abs(change)} puan`}
        </span>
      </div>
      <svg role="img" aria-label={summary} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="mt-2 h-24 w-full">
        {[0, 50, 100].map((tick) => (
          <line key={tick} x1={PADDING_X} x2={WIDTH - PADDING_X} y1={y(tick)} y2={y(tick)} strokeWidth="1" strokeDasharray={tick === 50 ? "3 3" : undefined} className="stroke-slate-200" />
        ))}
        <polyline points={coordinates.join(" ")} fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="stroke-indigo-600" />
        {points.map((point, index) => (
          <circle key={`${point.capturedAt}-${index}`} cx={x(index)} cy={y(point.score)} r={index === points.length - 1 ? 4.5 : 3} className={index === points.length - 1 ? "fill-indigo-600" : "fill-card stroke-indigo-600"} strokeWidth="2" />
        ))}
      </svg>
      <div aria-hidden="true" className="mt-1 flex justify-between text-xs text-slate-500">
        <span>{dateFormatter.format(new Date(first.capturedAt))} · {first.score}</span>
        <span>{dateFormatter.format(new Date(last.capturedAt))} · {last.score}</span>
      </div>
    </figure>
  );
}
