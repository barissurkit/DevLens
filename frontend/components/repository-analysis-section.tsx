"use client";

import { useMemo, useState } from "react";
import type {
  PortfolioRepositoryFailure,
  PortfolioRepositoryResult,
  RepositoryStructureSignals,
  ScoreDimensionResult,
  ExcludedPortfolioRepository,
} from "../lib/types";
import { categoryLabel, scoreTone } from "../lib/presentation";
import { buildRepositoryFixPrompt } from "../lib/fix-prompt";
import { PromptBox } from "./prompt-box";
import { ScoreDimension } from "./score-dimension";

interface RepositoryAnalysisSectionProps {
  repositories: PortfolioRepositoryResult[];
  failures: PortfolioRepositoryFailure[];
  excluded: ExcludedPortfolioRepository[];
  /** Login of the portfolio's owner; enables the per-repository prompt for fixing a repository. */
  owner?: string;
}

const STRUCTURE_LABELS: Array<[keyof RepositoryStructureSignals, string]> = [
  ["has_tests", "Test Yapısı"],
  ["has_ci", "CI İş Akışı"],
  ["has_gitignore", ".gitignore"],
  ["has_license", "LICENSE"],
  ["has_contributing", "CONTRIBUTING"],
  ["has_dockerfile", "Dockerfile"],
  ["has_compose", "Compose"],
  ["has_env_example", ".env.example"],
];

const README_LABELS: Array<[keyof PortfolioRepositoryResult["analysis"]["readme"], string]> = [
  ["exists", "README"],
  ["has_title", "Başlık"],
  ["has_description", "Açıklama"],
  ["has_installation", "Kurulum"],
  ["has_usage", "Kullanım"],
  ["has_technologies", "Teknolojiler"],
  ["has_requirements", "Gereksinimler"],
  ["has_images", "Görseller"],
  ["has_demo_link", "Demo Bağlantısı"],
];

const EXCLUSION_REASON_LABELS: Record<string, string> = {
  fork_repository: "Fork edilmiş repository",
  archived_repository: "Arşivlenmiş repository",
};

type SortKey = "default" | "score_desc" | "score_asc" | "name";

const SORT_OPTIONS: Array<[SortKey, string]> = [
  ["default", "Varsayılan sıra"],
  ["score_desc", "Skor: yüksekten düşüğe"],
  ["score_asc", "Skor: düşükten yükseğe"],
  ["name", "İsim: A → Z"],
];

const LOW_SCORE_THRESHOLD = 50;

function sortRepositories(repositories: PortfolioRepositoryResult[], sort: SortKey) {
  const sorted = [...repositories];
  if (sort === "score_desc") sorted.sort((a, b) => b.score.overall_score - a.score.overall_score);
  if (sort === "score_asc") sorted.sort((a, b) => a.score.overall_score - b.score.overall_score);
  if (sort === "name") sorted.sort((a, b) => a.repository.name.localeCompare(b.repository.name, "tr"));
  return sorted;
}

export function RepositoryAnalysisSection({ repositories, failures, excluded, owner }: RepositoryAnalysisSectionProps) {
  const hasAnyRepositoryState = repositories.length > 0 || failures.length > 0 || excluded.length > 0;
  const [sort, setSort] = useState<SortKey>("default");
  const [onlyPartial, setOnlyPartial] = useState(false);
  const [onlyLowScore, setOnlyLowScore] = useState(false);
  const visibleRepositories = useMemo(() => {
    const filtered = repositories.filter((item) => (!onlyPartial || item.score.is_partial) && (!onlyLowScore || item.score.overall_score < LOW_SCORE_THRESHOLD));
    return sortRepositories(filtered, sort);
  }, [repositories, sort, onlyPartial, onlyLowScore]);

  return (
    <section aria-labelledby="repository-analysis-heading" className="space-y-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand-700">Repository Analizi</p>
        <h3 id="repository-analysis-heading" className="mt-2 scroll-mt-20 text-2xl font-semibold tracking-tight text-slate-950">Repository kanıtları</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">Her repository için backend analizinin sunduğu deterministik kanıt sonuçları.</p>
      </div>

      {repositories.length > 1 && (
        <RepositoryControls
          sort={sort}
          onSortChange={setSort}
          onlyPartial={onlyPartial}
          onOnlyPartialChange={setOnlyPartial}
          onlyLowScore={onlyLowScore}
          onOnlyLowScoreChange={setOnlyLowScore}
          visibleCount={visibleRepositories.length}
          totalCount={repositories.length}
        />
      )}

      {repositories.length === 0 ? (
        <EmptyRepositoryState message="Başarılı repository analizi bulunmuyor." />
      ) : visibleRepositories.length > 0 ? (
        <div className="space-y-4">{visibleRepositories.map((repository) => <RepositoryCard key={repository.repository.html_url} result={repository} owner={owner} />)}</div>
      ) : <EmptyRepositoryState message="Seçilen filtrelerle eşleşen repository yok." />}

      {failures.length > 0 && <FailureSection failures={failures} />}
      {excluded.length > 0 && <ExcludedSection repositories={excluded} />}
      {!hasAnyRepositoryState && <p className="rounded-2xl border border-slate-200 bg-card p-5 text-sm text-slate-600">Bu analizde repository sonucu bulunmuyor.</p>}
    </section>
  );
}

interface RepositoryControlsProps {
  sort: SortKey;
  onSortChange: (sort: SortKey) => void;
  onlyPartial: boolean;
  onOnlyPartialChange: (value: boolean) => void;
  onlyLowScore: boolean;
  onOnlyLowScoreChange: (value: boolean) => void;
  visibleCount: number;
  totalCount: number;
}

function RepositoryControls({ sort, onSortChange, onlyPartial, onOnlyPartialChange, onlyLowScore, onOnlyLowScoreChange, visibleCount, totalCount }: RepositoryControlsProps) {
  const checkboxClass = "h-4 w-4 rounded border-slate-300 text-slate-950 focus:ring-2 focus:ring-brand-600";
  return (
    <div role="group" aria-label="Repository listesi sıralama ve filtreleme" className="print:hidden flex flex-col gap-4 rounded-2xl border border-slate-200 bg-card p-4 shadow-card sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-5">
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <span className="font-medium text-slate-900">Sırala</span>
          <select value={sort} onChange={(event) => onSortChange(event.target.value as SortKey)} className="min-h-10 rounded-lg border border-slate-300 bg-card px-3 text-sm text-slate-900 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20">
            {SORT_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={onlyPartial} onChange={(event) => onOnlyPartialChange(event.target.checked)} className={checkboxClass} />
          Yalnızca kısmi kanıtlı
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={onlyLowScore} onChange={(event) => onOnlyLowScoreChange(event.target.checked)} className={checkboxClass} />
          Yalnızca düşük skorlu (&lt; {LOW_SCORE_THRESHOLD})
        </label>
      </div>
      <p role="status" aria-live="polite" className="text-sm text-slate-500">{visibleCount} / {totalCount} repository gösteriliyor</p>
    </div>
  );
}

function RepositoryCard({ result, owner }: { result: PortfolioRepositoryResult; owner?: string }) {
  const { repository, analysis, score } = result;
  const fixPrompt = useMemo(() => (owner ? buildRepositoryFixPrompt(owner, result) : null), [owner, result]);
  const technologies = analysis.technologies.technologies;
  const categories = analysis.classification.categories;

  return (
    <details className="group rounded-2xl border border-slate-200 bg-card shadow-card">
      <summary className="grid cursor-pointer list-none grid-cols-[auto_minmax(0,1fr)] items-start gap-x-3 gap-y-3 rounded-xl p-5 outline-none transition focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center sm:p-6">
        <span aria-hidden="true" className="mt-1 shrink-0 text-xl leading-none text-slate-500 transition-transform group-open:rotate-90">›</span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="max-w-full break-words text-lg font-semibold text-slate-950">{repository.name}</span>
            {score.is_partial && <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">Kısmi kanıt</span>}
          </div>
          <p className="mt-2 break-words text-sm text-slate-600">{categoryLabel(analysis.classification.primary_category)}</p>
        </div>
        <div className="col-start-2 sm:col-start-auto sm:text-right">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">Repository Kanıt Skoru</p>
          <p className={`mt-1 text-2xl font-semibold ${scoreTone(score.overall_score).text}`}>{score.overall_score} / 100</p>
        </div>
      </summary>
      <div className="border-t border-slate-100 px-5 pb-6 pt-5 sm:px-6">
        <a href={repository.html_url} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center rounded-lg text-sm font-medium text-slate-700 underline decoration-slate-300 underline-offset-4 hover:text-slate-950 hover:decoration-slate-950 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2">Repository sayfasını aç</a>
        {score.is_partial && <p className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">Repository tree kısmi olduğu için yapı tabanlı kanıt eksik olabilir. Bu durum analiz hatası değildir.</p>}
        {score.limitations.length > 0 && <ul className="mb-5 space-y-2 text-sm text-slate-600">{score.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>}

        <div className="grid gap-4 md:grid-cols-3">{score.dimensions.map((dimension) => <ScoreDimension key={dimension.key} label={dimension.label} score={dimension.score} pointsEarned={dimension.points_earned} pointsPossible={dimension.points_possible} />)}</div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <EvidenceList title="README Sinyalleri" items={README_LABELS.filter(([key]) => analysis.readme[key]).map(([, label]) => label)} emptyMessage="Tespit edilen README sinyali yok." />
          <EvidenceList title="Repository Yapısı" items={STRUCTURE_LABELS.filter(([key]) => analysis.structure[key]).map(([, label]) => label)} emptyMessage="Tespit edilen yapı sinyali yok." />
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <ChipList title="Tespit Edilen Teknolojiler" items={technologies.map((technology) => technology.name)} emptyMessage="Bu repository için teknoloji sinyali bulunmuyor." />
          <ChipList title="Proje Kategorileri" items={categories.map((category) => categoryLabel(category.category))} emptyMessage="Bu repository için kategori sinyali bulunmuyor." />
        </div>
        <div className="mt-6"><RuleBreakdown dimensions={score.dimensions} /></div>
        {fixPrompt && (
          <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4 print:hidden">
            <h4 className="text-sm font-semibold text-slate-950">Yapay zekâ ile düzelt</h4>
            <p className="mt-1 text-sm leading-6 text-slate-600">Yalnızca bu repository&apos;nin eksikleri için hazır bir istem; kendi yapay zekâ asistanına ya da kod ajanına ver.</p>
            <div className="mt-3">
              <PromptBox prompt={fixPrompt} subject={repository.name} textLabel={`${repository.name} için düzeltme istemi`} />
            </div>
          </div>
        )}
      </div>
    </details>
  );
}

function RuleBreakdown({ dimensions }: { dimensions: ScoreDimensionResult[] }) {
  return <section aria-labelledby="repository-rules-heading"><h4 id="repository-rules-heading" className="text-sm font-semibold text-slate-950">Kanıt Dağılımı</h4><div className="mt-3 space-y-4">{dimensions.map((dimension) => <div key={dimension.key}><h5 className="text-sm font-medium text-slate-700">{dimension.label}</h5><ul className="mt-2 grid gap-2 sm:grid-cols-2">{dimension.rules.map((rule) => <li key={rule.key} className="rounded-lg border border-slate-200 p-3 text-sm"><div className="flex min-w-0 items-start gap-2"><span aria-hidden="true" className={rule.passed ? "text-emerald-700" : "text-slate-500"}>{rule.passed ? "✓" : "—"}</span><span className="min-w-0 break-words font-medium text-slate-800">{rule.label}</span><span className="ml-auto shrink-0 whitespace-nowrap text-xs text-slate-500">{rule.points_earned} / {rule.points_possible}</span></div><p className="mt-1 break-words pl-5 text-xs leading-5 text-slate-500">{rule.evidence}</p></li>)}</ul></div>)}</div></section>;
}

function EvidenceList({ title, items, emptyMessage }: { title: string; items: string[]; emptyMessage: string }) {
  return <section aria-labelledby={`${title}-heading`}><h4 id={`${title}-heading`} className="text-sm font-semibold text-slate-950">{title}</h4>{items.length > 0 ? <ul className="mt-3 flex flex-wrap gap-2">{items.map((item) => <li key={item} className="rounded-full bg-slate-100 px-3 py-1.5 text-sm text-slate-700">{item}</li>)}</ul> : <p className="mt-3 text-sm text-slate-500">{emptyMessage}</p>}</section>;
}

function ChipList({ title, items, emptyMessage }: { title: string; items: string[]; emptyMessage: string }) {
  return <EvidenceList title={title} items={items} emptyMessage={emptyMessage} />;
}

function FailureSection({ failures }: { failures: PortfolioRepositoryFailure[] }) {
  return <section aria-labelledby="repository-failures-heading" className="rounded-xl border border-amber-200 bg-amber-50 p-5 sm:p-6"><h4 id="repository-failures-heading" className="text-lg font-semibold text-amber-950">Repository Analiz Sorunları</h4><p className="mt-2 text-sm text-amber-900">Bu repository’ler için analiz verileri tamamlanamadı.</p><ul className="mt-4 space-y-3">{failures.map((failure) => <li key={`${failure.repository.html_url}-${failure.code}`} className="rounded-xl border border-amber-200 bg-card/70 p-4"><p className="break-words font-medium text-slate-950">{failure.repository.name}</p><p className="mt-1 text-sm leading-6 text-slate-700">{failure.message}</p></li>)}</ul></section>;
}

function ExcludedSection({ repositories }: { repositories: ExcludedPortfolioRepository[] }) {
  return <section aria-labelledby="excluded-repositories-heading" className="rounded-xl border border-slate-200 bg-slate-50 p-5 sm:p-6"><h4 id="excluded-repositories-heading" className="text-lg font-semibold text-slate-950">Hariç Tutulan Repository’ler</h4><p className="mt-2 text-sm text-slate-600">Bu repository’ler seçim politikası nedeniyle analiz kapsamı dışındadır.</p><ul className="mt-4 space-y-2">{repositories.map((item) => <li key={item.repository.html_url} className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg bg-card p-3 text-sm"><span className="break-words font-medium text-slate-800">{item.repository.name}</span><span className="break-words text-slate-500">{item.reasons.map((reason) => EXCLUSION_REASON_LABELS[reason] || "Seçim politikası").join(" · ")}</span></li>)}</ul></section>;
}

function EmptyRepositoryState({ message }: { message: string }) {
  return <p className="rounded-2xl border border-slate-200 bg-card p-5 text-sm text-slate-600">{message}</p>;
}
