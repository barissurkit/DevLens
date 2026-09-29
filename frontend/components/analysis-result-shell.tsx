import { useEffect, useRef } from "react";
import type {
  GitHubPortfolioInterpretationResponse,
  PortfolioInsight,
  PortfolioScoreDimensionResult,
} from "../lib/types";
import { PortfolioInterpretationSection } from "./portfolio-interpretation-section";
import { ActionPlan } from "./action-plan";
import { AISuggestedActions } from "./ai-suggested-actions";
import { AnalysisHistory } from "./analysis-history";
import { RepositoryAnalysisSection } from "./repository-analysis-section";
import { ScoreDimension } from "./score-dimension";
import { GuidedImprovementSection } from "./guided-improvement-section";
import { categoryLabel, portfolioModeLabel, scoreTone } from "../lib/presentation";

interface AnalysisResultShellProps {
  result: GitHubPortfolioInterpretationResponse;
  onReanalyze: () => void;
}

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

export function AnalysisResultShell({ result, onReanalyze }: AnalysisResultShellProps) {
  const dashboardHeadingRef = useRef<HTMLHeadingElement>(null);
  const { analysis, interpretation, viewer_context } = result;
  const { aggregation, intelligence, score, selection, user } = analysis;
  const dimensions = orderDimensions(score.dimensions);
  const limitations = uniqueItems([...score.limitations, ...intelligence.limitations]);
  const isPartial = score.is_partial || aggregation.has_failures || aggregation.partial_evidence_repository_count > 0;

  useEffect(() => {
    dashboardHeadingRef.current?.focus();
  }, []);

  return (
    <section aria-labelledby="portfolio-dashboard" className="space-y-6">
      <SectionNav />
      <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.16em] text-emerald-600">
              {portfolioModeLabel(viewer_context)}
            </p>
            <h2 ref={dashboardHeadingRef} id="portfolio-dashboard" tabIndex={-1} className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-950 focus:ring-offset-2 sm:text-3xl">
              {user.name || `@${user.username}`} portföyü
            </h2>
            <p className="mt-2 text-slate-600">@{user.username} için herkese açık GitHub kanıtları incelendi.</p>
          </div>
          <a href={user.html_url} target="_blank" rel="noreferrer" className="text-sm font-medium text-slate-700 underline decoration-slate-300 underline-offset-4 hover:text-slate-950">
            GitHub profilini aç
          </a>
        </div>
        {isPartial && <p className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">Bu sonuç, bazı repository verileri eksik olduğu için kısmi kanıt içerebilir.</p>}
      </header>

      <section aria-labelledby="score-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          {score.is_available && score.overall_score !== null && <ScoreGauge score={score.overall_score} />}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500">Portföy Kanıt Skoru</p>
            <h3 id="score-heading" className={`mt-3 scroll-mt-20 text-5xl font-semibold tracking-tight ${score.is_available && score.overall_score !== null ? scoreTone(score.overall_score).text : "text-slate-950"}`}>
              {score.is_available && score.overall_score !== null ? `${score.overall_score} / 100` : "Kullanılamıyor"}
            </h3>
            <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600">Herkese açık repository&apos;lerde gözlemlenebilen dokümantasyon ve mühendislik pratiği sinyallerine dayalı deterministik portföy skoru.</p>
            <p className="mt-3 text-sm text-slate-500">
              {score.is_available ? `${score.scored_repository_count} başarılı repository üzerinden hesaplandı.` : score.limitations[0] || "Yeterli başarılı repository bulunmadığı için skor hesaplanamadı."}
            </p>
          </div>
          {score.is_partial && <span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800">Kısmi kanıt</span>}
        </div>
        {dimensions.length > 0 ? <div className="mt-8 grid gap-4 md:grid-cols-3">{dimensions.map((dimension) => <ScoreDimension key={dimension.key} label={DIMENSION_LABELS[dimension.key] || dimension.label} score={dimension.score} pointsEarned={dimension.points_earned} pointsPossible={dimension.points_possible} description={DIMENSION_DESCRIPTIONS[dimension.key] || dimension.label} />)}</div> : <p className="mt-8 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">Skor kullanılabilir olduğunda boyut dağılımı burada görünecek.</p>}
      </section>

      <section aria-labelledby="stats-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <SectionHeading id="stats-heading" title="Portföy istatistikleri" />
        <div className="mt-5 grid grid-cols-1 gap-3 min-[420px]:grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
          <StatItem label="Herkese açık repository" value={user.public_repos} />
          <StatItem label="Seçilen" value={aggregation.selected_repository_count} />
          <StatItem label="Hariç tutulan" value={selection.excluded.length} />
          <StatItem label="Başarılı analiz" value={aggregation.successful_repository_count} />
          <StatItem label="Başarısız analiz" value={aggregation.failed_repository_count} />
          <StatItem label="Kısmi kanıt" value={aggregation.partial_evidence_repository_count} />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <InsightSection id="strengths-heading" title="Güçlü Kanıt Sinyalleri" items={intelligence.strength_signals} emptyMessage="Portföy genelinde tekrar eden güçlü kanıt sinyali belirlenmedi." />
        <InsightSection id="improvements-heading" title="Gelişim Alanları" items={intelligence.improvement_signals} emptyMessage="Bu analizde portföy genelinde tekrarlayan bir gelişim alanı belirlenmedi." />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <TagSection id="technologies-heading" title="Sık Tekrarlanan Teknolojiler" description="Birden fazla analiz edilen repository&apos;de tespit edilen teknolojiler." items={intelligence.recurring_technologies.map((item) => `${item.technology} · ${item.repository_count}`)} emptyMessage="Birden fazla repository&apos;de tekrar eden teknoloji tespit edilmedi." />
        <TagSection id="areas-heading" title="Öne Çıkan Proje Alanları" description="Portföy içinde tekrar eden proje kategorileri." items={intelligence.dominant_areas.map((item) => `${categoryLabel(item.category)} · ${item.repository_count}`)} emptyMessage="Portföy içinde öne çıkan tekrar eden proje alanı belirlenmedi." />
      </div>

      {limitations.length > 0 && <section aria-labelledby="limitations-heading" className="rounded-2xl border border-slate-200 bg-slate-50 p-6 sm:p-8"><SectionHeading id="limitations-heading" title="Analiz notları" /><ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-slate-600">{limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></section>}

      <PortfolioInterpretationSection analysis={analysis} interpretation={interpretation} />
      {viewer_context.is_owner && <GuidedImprovementSection improvements={result.guided_improvements} onReanalyze={onReanalyze} />}
      {viewer_context.mode === "my_workspace" && <>
        <AnalysisHistory key={user.username} visible={viewer_context.is_owner} />
        <AISuggestedActions key={user.username} username={user.username} />
        <ActionPlan />
      </>}
      <RepositoryAnalysisSection repositories={analysis.repository_analysis.repositories} failures={analysis.repository_analysis.failures} excluded={selection.excluded} />
    </section>
  );
}

const SECTION_LINKS: Array<[string, string]> = [
  ["#score-heading", "Skor"],
  ["#stats-heading", "İstatistikler"],
  ["#ai-interpretation-heading", "AI Yorumu"],
  ["#repository-analysis-heading", "Repository'ler"],
];

function SectionNav() {
  return (
    <nav aria-label="Sonuç bölümleri" className="sticky top-0 z-10 -mx-2 overflow-x-auto bg-slate-50/90 px-2 py-2 backdrop-blur">
      <ul className="flex min-w-max gap-2">
        {SECTION_LINKS.map(([href, label]) => (
          <li key={href}>
            <a href={href} className="inline-flex min-h-10 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2">{label}</a>
          </li>
        ))}
      </ul>
    </nav>
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
    <div className="flex shrink-0 flex-row items-center gap-3 lg:flex-col">
      <svg aria-hidden="true" viewBox="0 0 100 100" className="h-20 w-20 -rotate-90 lg:h-28 lg:w-28">
        <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="9" className="stroke-slate-100" />
        <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="9" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={circumference * (1 - progress / 100)} className={tone.stroke} />
      </svg>
      <span className={`rounded-full px-3 py-1 text-xs font-medium ${tone.badge}`}>{tone.label}</span>
    </div>
  );
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
