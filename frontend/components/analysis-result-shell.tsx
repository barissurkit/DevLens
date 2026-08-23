import type {
  GitHubPortfolioAnalysis,
  PortfolioInsight,
  PortfolioScoreDimensionResult,
} from "../lib/types";
import { RepositoryAnalysisSection } from "./repository-analysis-section";

interface AnalysisResultShellProps {
  result: GitHubPortfolioAnalysis;
}

const DIMENSION_ORDER = ["documentation_consistency", "testing_automation_adoption", "repository_hygiene_consistency"];
const DIMENSION_LABELS: Record<string, string> = {
  documentation_consistency: "Dokümantasyon",
  testing_automation_adoption: "Test ve Otomasyon",
  repository_hygiene_consistency: "Repository Hijyeni",
};
const DIMENSION_DESCRIPTIONS: Record<string, string> = {
  documentation_consistency: "README dokümantasyon sinyallerinin portfolio genelindeki tutarlılığı.",
  testing_automation_adoption: "Test yapısı ve CI workflow sinyallerinin portfolio genelindeki görünümü.",
  repository_hygiene_consistency: ".gitignore, LICENSE ve CONTRIBUTING gibi repository pratiği sinyallerinin görünümü.",
};

export function AnalysisResultShell({ result }: AnalysisResultShellProps) {
  const { aggregation, intelligence, score, selection, user } = result;
  const dimensions = orderDimensions(score.dimensions);
  const limitations = uniqueItems([...score.limitations, ...intelligence.limitations]);
  const isPartial = score.is_partial || aggregation.has_failures || aggregation.partial_evidence_repository_count > 0;

  return (
    <section aria-labelledby="portfolio-dashboard" className="space-y-6">
      <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.16em] text-emerald-600">Analiz tamamlandı</p>
            <h2 id="portfolio-dashboard" className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
              {user.name || `@${user.username}`} portföyü
            </h2>
            <p className="mt-2 text-slate-600">@{user.username} için herkese açık GitHub kanıtları incelendi.</p>
          </div>
          <a href={user.html_url} target="_blank" rel="noreferrer" className="text-sm font-medium text-slate-700 underline decoration-slate-300 underline-offset-4 hover:text-slate-950">
            GitHub profilini aç
          </a>
        </div>
        {isPartial && <p className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">Bu sonuç, bazı repository verileri eksik olduğu için kısmi evidence içerebilir.</p>}
      </header>

      <section aria-labelledby="score-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500">Portfolio Evidence Score</p>
            <h3 id="score-heading" className="mt-3 text-5xl font-semibold tracking-tight text-slate-950">
              {score.is_available && score.overall_score !== null ? `${score.overall_score} / 100` : "Kullanılamıyor"}
            </h3>
            <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600">Public repository&apos;lerde gözlemlenebilen documentation ve engineering-practice sinyallerine dayalı deterministic portfolio skoru.</p>
            <p className="mt-3 text-sm text-slate-500">
              {score.is_available ? `${score.scored_repository_count} başarılı repository üzerinden hesaplandı.` : score.limitations[0] || "Yeterli başarılı repository bulunmadığı için skor hesaplanamadı."}
            </p>
          </div>
          {score.is_partial && <span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800">Kısmi evidence</span>}
        </div>
        {dimensions.length > 0 ? <div className="mt-8 grid gap-4 md:grid-cols-3">{dimensions.map((dimension) => <ScoreDimension key={dimension.key} dimension={dimension} />)}</div> : <p className="mt-8 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">Skor kullanılabilir olduğunda dimension breakdown burada görünecek.</p>}
      </section>

      <section aria-labelledby="stats-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <SectionHeading id="stats-heading" title="Portfolio istatistikleri" />
        <div className="mt-5 grid grid-cols-1 gap-3 min-[420px]:grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
          <StatItem label="Public repository" value={user.public_repos} />
          <StatItem label="Seçilen" value={aggregation.selected_repository_count} />
          <StatItem label="Hariç tutulan" value={selection.excluded.length} />
          <StatItem label="Başarılı analiz" value={aggregation.successful_repository_count} />
          <StatItem label="Başarısız analiz" value={aggregation.failed_repository_count} />
          <StatItem label="Kısmi evidence" value={aggregation.partial_evidence_repository_count} />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <InsightSection id="strengths-heading" title="Güçlü Evidence Sinyalleri" items={intelligence.strength_signals} emptyMessage="Portfolio genelinde tekrar eden güçlü evidence sinyali belirlenmedi." />
        <InsightSection id="improvements-heading" title="İyileştirme Fırsatları" items={intelligence.improvement_signals} emptyMessage="Bu analizde portfolio genelinde tekrarlayan bir improvement opportunity belirlenmedi." />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <TagSection id="technologies-heading" title="Sık Tekrarlanan Teknolojiler" description="Birden fazla analyzed repository&apos;de tespit edilen teknolojiler." items={intelligence.recurring_technologies.map((item) => `${item.technology} · ${item.repository_count}`)} emptyMessage="Birden fazla repository&apos;de tekrar eden teknoloji tespit edilmedi." />
        <TagSection id="areas-heading" title="Öne Çıkan Proje Alanları" description="Portfolio içinde tekrar eden proje kategorileri." items={intelligence.dominant_areas.map((item) => `${item.category} · ${item.repository_count}`)} emptyMessage="Portfolio içinde öne çıkan tekrar eden proje alanı belirlenmedi." />
      </div>

      {limitations.length > 0 && <section aria-labelledby="limitations-heading" className="rounded-2xl border border-slate-200 bg-slate-50 p-6 sm:p-8"><SectionHeading id="limitations-heading" title="Analiz notları" /><ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-slate-600">{limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></section>}

      <RepositoryAnalysisSection repositories={result.repository_analysis.repositories} failures={result.repository_analysis.failures} excluded={selection.excluded} />
    </section>
  );
}

function orderDimensions(dimensions: PortfolioScoreDimensionResult[]) {
  return [...dimensions].sort((left, right) => {
    const leftIndex = DIMENSION_ORDER.indexOf(left.key);
    const rightIndex = DIMENSION_ORDER.indexOf(right.key);
    return (leftIndex === -1 ? DIMENSION_ORDER.length : leftIndex) - (rightIndex === -1 ? DIMENSION_ORDER.length : rightIndex);
  });
}

function ScoreDimension({ dimension }: { dimension: PortfolioScoreDimensionResult }) {
  const progress = Number.isFinite(dimension.score) ? Math.min(100, Math.max(0, dimension.score)) : 0;
  const label = DIMENSION_LABELS[dimension.key] || dimension.label;
  return <article className="min-w-0 rounded-xl bg-slate-50 p-4"><div className="flex flex-wrap items-baseline justify-between gap-2"><h4 className="min-w-0 font-medium text-slate-950">{label}</h4><span className="shrink-0 text-sm font-semibold text-slate-700">{dimension.points_earned} / {dimension.points_possible}</span></div><p className="mt-2 text-xs leading-5 text-slate-500">{DIMENSION_DESCRIPTIONS[dimension.key] || dimension.label}</p><div role="progressbar" aria-label={`${label} skoru`} aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-slate-700" style={{ width: `${progress}%` }} /></div></article>;
}

function StatItem({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs leading-5 text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p></div>;
}

function SectionHeading({ id, title }: { id: string; title: string }) {
  return <h3 id={id} className="text-xl font-semibold tracking-tight text-slate-950">{title}</h3>;
}

function InsightSection({ id, title, items, emptyMessage }: { id: string; title: string; items: PortfolioInsight[]; emptyMessage: string }) {
  return <section aria-labelledby={id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><SectionHeading id={id} title={title} />{items.length > 0 ? <ul className="mt-5 space-y-3">{items.map((item) => <li key={item.key} className="rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">{item.message}</li>)}</ul> : <p className="mt-5 text-sm leading-6 text-slate-500">{emptyMessage}</p>}</section>;
}

function TagSection({ id, title, description, items, emptyMessage }: { id: string; title: string; description: string; items: string[]; emptyMessage: string }) {
  return <section aria-labelledby={id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><SectionHeading id={id} title={title} /><p className="mt-2 text-sm text-slate-500">{description}</p>{items.length > 0 ? <ul className="mt-5 flex flex-wrap gap-2" aria-label={title}>{items.map((item) => <li key={item} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700">{item}</li>)}</ul> : <p className="mt-5 text-sm leading-6 text-slate-500">{emptyMessage}</p>}</section>;
}

function uniqueItems(items: string[]) {
  return [...new Set(items)];
}
