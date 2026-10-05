import { scoreTone } from "../lib/presentation";

interface ScoreDimensionProps {
  label: string;
  score: number;
  pointsEarned: number;
  pointsPossible: number;
  description?: string;
}

export function ScoreDimension({ label, score, pointsEarned, pointsPossible, description }: ScoreDimensionProps) {
  const progress = Number.isFinite(score) ? Math.min(100, Math.max(0, score)) : 0;
  return (
    <article className="min-w-0 rounded-xl bg-slate-50 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="min-w-0 font-medium text-slate-950">{label}</h4>
        <span className="shrink-0 text-sm font-semibold text-slate-700">{pointsEarned} / {pointsPossible} puan</span>
      </div>
      {description && <p className="mt-2 text-xs leading-5 text-slate-500">{description}</p>}
      <div role="progressbar" aria-label={`${label} skoru`} aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${scoreTone(progress).fill}`} style={{ width: `${progress}%` }} />
      </div>
    </article>
  );
}
