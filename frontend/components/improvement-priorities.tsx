import type { PortfolioScoreDimensionResult } from "../lib/types";
import { topImprovements } from "../lib/priorities";

interface ImprovementPrioritiesProps {
  dimensions: PortfolioScoreDimensionResult[];
  overallScore: number | null;
}

const formatPoints = (value: number) => value.toLocaleString("tr-TR", { maximumFractionDigits: 1 });

/** The steps that would raise the portfolio score the most, ranked by the points they could add. */
export function ImprovementPriorities({ dimensions, overallScore }: ImprovementPrioritiesProps) {
  const improvements = topImprovements(dimensions);
  if (improvements.length === 0) return null;

  const rawGain = improvements.reduce((sum, item) => sum + item.points, 0);
  const totalGain = Math.round(overallScore === null ? rawGain : Math.min(rawGain, 100 - overallScore));

  return (
    <section aria-labelledby="priorities-heading" className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-5 shadow-card sm:p-6">
      <h3 id="priorities-heading" className="text-base font-semibold tracking-tight text-slate-950">Önce şunu yap</h3>
      <p className="mt-1 text-sm text-slate-600">Skoru en çok artıracak adımlar. Puan, kuralın ağırlığı × eksik repository oranıdır.</p>
      <ol className="mt-4 space-y-2">
        {improvements.map((item, index) => (
          <li key={item.key} className="flex items-center gap-3 rounded-lg bg-card px-4 py-3 ring-1 ring-slate-200">
            <span aria-hidden="true" className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white">{index + 1}</span>
            <div className="min-w-0 flex-1">
              <p className="break-words text-sm font-medium text-slate-950">{item.label}</p>
              <p className="text-xs text-slate-500">{item.analyzedRepositories} repository&apos;nin {item.missingRepositories} tanesinde eksik</p>
            </div>
            <span className="shrink-0 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">+{formatPoints(item.points)} puan</span>
          </li>
        ))}
      </ol>
      {totalGain > 0 && (
        <p className="mt-3 text-sm text-slate-700">
          Bu adımları tamamlamak skoru yaklaşık <strong className="font-semibold text-slate-950">+{totalGain} puan</strong> artırabilir.
        </p>
      )}
    </section>
  );
}
