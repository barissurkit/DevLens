import type { GitHubPortfolioAnalysis } from "../lib/types";

interface AnalysisResultShellProps {
  result: GitHubPortfolioAnalysis;
}

export function AnalysisResultShell({ result }: AnalysisResultShellProps) {
  const { aggregation, score, user } = result;

  return (
    <section aria-labelledby="analysis-complete" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <p className="text-sm font-medium uppercase tracking-[0.16em] text-emerald-600">Tamamlandı</p>
      <h2 id="analysis-complete" className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        Portföy analizi hazır
      </h2>
      <p className="mt-2 text-slate-600">@{user.username} için herkese açık GitHub kanıtları incelendi.</p>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <SummaryItem label="Seçilen repository" value={aggregation.selected_repository_count} />
        <SummaryItem label="Başarılı analiz" value={aggregation.successful_repository_count} />
        <SummaryItem
          label="Portfolio Evidence Score"
          value={score.is_available && score.overall_score !== null ? `${score.overall_score} / 100` : "Kullanılamıyor"}
        />
      </div>
      <p className="mt-5 text-sm leading-6 text-slate-500">
        Skor, analiz edilen herkese açık repository&apos;lerde gözlemlenen dokümantasyon ve mühendislik pratiklerine dayanır.
      </p>
    </section>
  );
}

function SummaryItem({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-950">{value}</p>
    </div>
  );
}
