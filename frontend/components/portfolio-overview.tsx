import type { GitHubPortfolioAnalysis, PortfolioInsight, PortfolioRepositoryResult, PortfolioScoreDimensionResult } from "../lib/types";
import { categoryLabel, scoreTone } from "../lib/presentation";
import { ImprovementPriorities } from "./improvement-priorities";
import { ScoreDimension } from "./score-dimension";
import { ScoreMethodology } from "./score-methodology";
import { SignalDetail } from "./signal-detail";

const DIMENSION_ORDER = ["documentation_consistency", "testing_automation_adoption", "repository_hygiene_consistency"];
const DIMENSION_LABELS: Record<string, string> = {
  documentation_consistency: "Dokümantasyon",
  testing_automation_adoption: "Test ve Otomasyon",
  repository_hygiene_consistency: "Repository Hijyeni",
};
const DIMENSION_DESCRIPTIONS: Record<string, string> = {
  documentation_consistency: "README dokümantasyon sinyallerinin portföy genelindeki tutarlılığı.",
  testing_automation_adoption: "Test yapısı ve CI iş akışı sinyallerinin portföy genelindeki görünümü.",
  repository_hygiene_consistency: ".gitignore, LICENSE ve CONTRIBUTING gibi repository pratiği sinyallerinin görünümü.",
};

const cardClass = "rounded-2xl border border-slate-200 bg-card p-5 shadow-card sm:p-6";

export function PortfolioOverview({ analysis }: { analysis: GitHubPortfolioAnalysis }) {
  const { aggregation, intelligence, score, selection, user } = analysis;
  const limitations = uniqueItems([...score.limitations, ...intelligence.limitations]);
  const repositories = analysis.repository_analysis.repositories;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-3 lg:items-start">
        <ScoreCard analysis={analysis} className="lg:col-span-2" />
        <section aria-labelledby="stats-heading" className={cardClass}>
          <SectionHeading id="stats-heading" title="Analiz kapsamı" />
          <dl className="mt-4 divide-y divide-slate-100 text-sm">
            <StatRow label="Herkese açık repository" value={user.public_repos} />
            <StatRow label="Seçilen" value={aggregation.selected_repository_count} />
            <StatRow label="Hariç tutulan" value={selection.excluded.length} />
            <StatRow label="Başarılı analiz" value={aggregation.successful_repository_count} />
            <StatRow label="Başarısız analiz" value={aggregation.failed_repository_count} tone={aggregation.failed_repository_count > 0 ? "warn" : undefined} />
            <StatRow label="Kısmi kanıt" value={aggregation.partial_evidence_repository_count} tone={aggregation.partial_evidence_repository_count > 0 ? "warn" : undefined} />
          </dl>
        </section>
      </div>

      {score.is_available && <ImprovementPriorities dimensions={score.dimensions} overallScore={score.overall_score} />}

      <div className="grid gap-6 lg:grid-cols-2">
        <InsightSection id="strengths-heading" title="Güçlü Kanıt Sinyalleri" tone="positive" items={intelligence.strength_signals} repositories={repositories} emptyMessage="Portföy genelinde tekrar eden güçlü kanıt sinyali belirlenmedi." />
        <InsightSection id="improvements-heading" title="Gelişim Alanları" tone="attention" items={intelligence.improvement_signals} repositories={repositories} emptyMessage="Bu analizde portföy genelinde tekrarlayan bir gelişim alanı belirlenmedi." />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <TagSection id="technologies-heading" title="Sık Tekrarlanan Teknolojiler" description="Birden fazla analiz edilen repository&apos;de tespit edilen teknolojiler." items={intelligence.recurring_technologies.map((item) => `${item.technology} · ${item.repository_count}`)} emptyMessage="Birden fazla repository&apos;de tekrar eden teknoloji tespit edilmedi." />
        <TagSection id="areas-heading" title="Öne Çıkan Proje Alanları" description="Portföy içinde tekrar eden proje kategorileri." items={intelligence.dominant_areas.map((item) => `${categoryLabel(item.category)} · ${item.repository_count}`)} emptyMessage="Portföy içinde öne çıkan tekrar eden proje alanı belirlenmedi." />
      </div>

      {limitations.length > 0 && (
        <section aria-labelledby="limitations-heading" className="rounded-xl border border-slate-200 bg-slate-50 p-5 sm:p-6">
          <SectionHeading id="limitations-heading" title="Analiz notları" />
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-slate-600">{limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
        </section>
      )}
    </div>
  );
}

function ScoreCard({ analysis, className = "" }: { analysis: GitHubPortfolioAnalysis; className?: string }) {
  const { score } = analysis;
  const hasScore = score.is_available && score.overall_score !== null;
  const dimensions = orderDimensions(score.dimensions);
  return (
    <section aria-labelledby="score-heading" className={`${cardClass} ${className}`}>
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
        {hasScore && score.overall_score !== null && <ScoreGauge score={score.overall_score} />}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Portföy Kanıt Skoru</p>
            {score.is_partial && <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800">Kısmi kanıt</span>}
          </div>
          <h3 id="score-heading" className={`mt-2 text-4xl font-semibold tracking-tight sm:text-5xl ${hasScore && score.overall_score !== null ? scoreTone(score.overall_score).text : "text-slate-950"}`}>
            {hasScore ? `${score.overall_score} / 100` : "Kullanılamıyor"}
          </h3>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600">Herkese açık repository&apos;lerde gözlemlenebilen dokümantasyon ve mühendislik pratiği sinyallerine dayalı deterministik portföy skoru.</p>
          <p className="mt-1 text-sm text-slate-500">
            {score.is_available ? `${score.scored_repository_count} başarılı repository üzerinden hesaplandı.` : score.limitations[0] || "Yeterli başarılı repository bulunmadığı için skor hesaplanamadı."}
          </p>
        </div>
      </div>
      {dimensions.length > 0
        ? <div className="mt-6 grid gap-4 border-t border-slate-100 pt-6 md:grid-cols-3">{dimensions.map((dimension) => <ScoreDimension key={dimension.key} label={DIMENSION_LABELS[dimension.key] || dimension.label} score={dimension.score} pointsEarned={dimension.points_earned} pointsPossible={dimension.points_possible} description={DIMENSION_DESCRIPTIONS[dimension.key] || dimension.label} />)}</div>
        : <p className="mt-6 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600">Skor kullanılabilir olduğunda boyut dağılımı burada görünecek.</p>}
      <ScoreMethodology
        dimensions={dimensions.map((dimension) => ({ ...dimension, label: DIMENSION_LABELS[dimension.key] || dimension.label }))}
        scoredRepositoryCount={score.scored_repository_count}
      />
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

function ScoreGauge({ score }: { score: number }) {
  const tone = scoreTone(score);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(100, Math.max(0, score));
  return (
    <div className="flex shrink-0 flex-row items-center gap-3 sm:flex-col">
      <div className="relative h-28 w-28 sm:h-32 sm:w-32">
        <svg aria-hidden="true" viewBox="0 0 100 100" className="h-full w-full -rotate-90">
          <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="9" className="stroke-slate-100" />
          <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="9" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={circumference * (1 - progress / 100)} className={`${tone.stroke} transition-[stroke-dashoffset] duration-700 motion-reduce:transition-none`} />
        </svg>
        <span aria-hidden="true" className={`absolute inset-0 flex items-center justify-center text-3xl font-semibold tracking-tight sm:text-4xl ${tone.text}`}>{progress}</span>
      </div>
      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${tone.badge}`}>{tone.label}</span>
    </div>
  );
}

function StatRow({ label, value, tone }: { label: string; value: number; tone?: "warn" }) {
  return (
    <div className="flex items-center justify-between py-2.5">
      <dt className="text-slate-600">{label}</dt>
      <dd className={`font-semibold ${tone === "warn" ? "text-amber-700" : "text-slate-950"}`}>{value}</dd>
    </div>
  );
}

function SectionHeading({ id, title }: { id: string; title: string }) {
  return <h3 id={id} className="text-base font-semibold tracking-tight text-slate-950">{title}</h3>;
}

const INSIGHT_ACCENT = { positive: "border-l-emerald-500", attention: "border-l-amber-500" } as const;

function InsightSection({ id, title, tone, items, repositories, emptyMessage }: { id: string; title: string; tone: keyof typeof INSIGHT_ACCENT; items: PortfolioInsight[]; repositories: PortfolioRepositoryResult[]; emptyMessage: string }) {
  return (
    <section aria-labelledby={id} className={cardClass}>
      <SectionHeading id={id} title={title} />
      {items.length > 0
        ? <ul className="mt-4 space-y-3">{items.map((item) => (
            <li key={item.key} className={`rounded-lg border-l-4 bg-slate-50 p-4 text-sm leading-6 text-slate-700 ${INSIGHT_ACCENT[tone]}`}>
              <p>{item.message}</p>
              <CoverageMeter detected={item.detected_repository_count} analyzed={item.analyzed_repository_count} tone={tone} />
              <SignalDetail signalKey={item.key} repositories={repositories} />
            </li>
          ))}</ul>
        : <p className="mt-4 text-sm leading-6 text-slate-500">{emptyMessage}</p>}
    </section>
  );
}

const METER_FILL = { positive: "bg-emerald-500", attention: "bg-amber-500" } as const;

/** Shows in how many of the analyzed repositories a signal was found, e.g. "2 / 6 repository". */
function CoverageMeter({ detected, analyzed, tone }: { detected: number; analyzed: number; tone: keyof typeof INSIGHT_ACCENT }) {
  if (analyzed <= 0) return null;
  const percent = Math.min(100, Math.max(0, Math.round((detected / analyzed) * 100)));
  return (
    <div className="mt-3 flex items-center gap-3">
      <div aria-hidden="true" className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${METER_FILL[tone]}`} style={{ width: `${percent}%` }} />
      </div>
      <span className="shrink-0 text-xs font-semibold text-slate-700">
        {detected} / {analyzed} repository
        <span className="sr-only"> (yaklaşık %{percent})</span>
      </span>
    </div>
  );
}

function TagSection({ id, title, description, items, emptyMessage }: { id: string; title: string; description: string; items: string[]; emptyMessage: string }) {
  return (
    <section aria-labelledby={id} className={cardClass}>
      <SectionHeading id={id} title={title} />
      <p className="mt-1 text-sm text-slate-500">{description}</p>
      {items.length > 0
        ? <ul className="mt-4 flex flex-wrap gap-2" aria-label={title}>{items.map((item) => <li key={item} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700">{item}</li>)}</ul>
        : <p className="mt-4 text-sm leading-6 text-slate-500">{emptyMessage}</p>}
    </section>
  );
}

function uniqueItems(items: string[]) {
  return [...new Set(items)];
}
