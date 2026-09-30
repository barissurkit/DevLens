import type { GuidedImprovement } from "../lib/types";
import { GuidedImprovementCard } from "./guided-improvement-card";

interface GuidedImprovementSectionProps {
  improvements: GuidedImprovement[];
  onReanalyze: () => void;
}

export function GuidedImprovementSection({ improvements, onReanalyze }: GuidedImprovementSectionProps) {
  if (improvements.length === 0) return null;

  return <section aria-labelledby="guided-improvement-heading" className="rounded-xl border border-emerald-200 bg-card p-6 shadow-card sm:p-8">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-700">İyileştir</p>
        <h3 id="guided-improvement-heading" className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">Guided Improvement</h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Aşağıdaki adımları repository&apos;lerinde manuel olarak uyguladıktan sonra sonucu tekrar analiz edebilirsin.</p>
      </div>
      <button type="button" onClick={onReanalyze} className="min-h-11 shrink-0 rounded-xl bg-indigo-600 px-4 text-sm font-medium text-white transition hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2">Tekrar analiz et</button>
    </div>
    <div className="mt-6 space-y-4">{improvements.map((item) => <GuidedImprovementCard key={item.rule_key} item={item} />)}</div>
  </section>;
}
