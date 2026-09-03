import type { GuidedImprovement } from "../lib/types";

export function GuidedImprovementCard({ item }: { item: GuidedImprovement }) {
  const statusLabel = item.verification.current_state === "needs_improvement"
    ? "İyileştirme gerekiyor"
    : "Mevcut kriter karşılanıyor";

  return <article className="rounded-xl border border-amber-200 bg-amber-50/50 p-5">
    <h4 className="text-lg font-semibold text-slate-950">{item.title}</h4>
    <div className="mt-4 space-y-4 text-sm leading-6 text-slate-700">
      <div>
        <h5 className="font-medium text-slate-900">Neden önemli?</h5>
        <p className="mt-1">{item.why}</p>
      </div>
      <div>
        <h5 className="font-medium text-slate-900">Nasıl iyileştirebilirsin?</h5>
        <ol className="mt-2 list-decimal space-y-2 pl-5">
          {item.steps.map((step, index) => <li key={`${item.rule_key}-step-${index}`}>{step}</li>)}
        </ol>
      </div>
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h5 className="font-medium text-slate-900">Doğrulama</h5>
        <p className="mt-1">Durum: {statusLabel}</p>
        <p className="mt-1 text-slate-600">{item.verification.detected_repository_count} repository tespit edildi, {item.verification.analyzed_repository_count} repository analiz edildi.</p>
        {item.verification.reanalysis_required && <p className="mt-1 text-slate-600">Değişikliklerden sonra tekrar analiz gerekli.</p>}
      </div>
    </div>
  </article>;
}
