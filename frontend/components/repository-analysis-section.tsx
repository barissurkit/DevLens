import type {
  PortfolioRepositoryFailure,
  PortfolioRepositoryResult,
  RepositoryStructureSignals,
  ScoreDimensionResult,
  ExcludedPortfolioRepository,
} from "../lib/types";

interface RepositoryAnalysisSectionProps {
  repositories: PortfolioRepositoryResult[];
  failures: PortfolioRepositoryFailure[];
  excluded: ExcludedPortfolioRepository[];
}

const STRUCTURE_LABELS: Array<[keyof RepositoryStructureSignals, string]> = [
  ["has_tests", "Tests structure"],
  ["has_ci", "CI workflow"],
  ["has_gitignore", ".gitignore"],
  ["has_license", "LICENSE"],
  ["has_contributing", "CONTRIBUTING"],
  ["has_dockerfile", "Dockerfile"],
  ["has_compose", "Compose"],
  ["has_env_example", ".env.example"],
];

const README_LABELS: Array<[keyof PortfolioRepositoryResult["analysis"]["readme"], string]> = [
  ["exists", "README"],
  ["has_title", "Title"],
  ["has_description", "Description"],
  ["has_installation", "Installation"],
  ["has_usage", "Usage"],
  ["has_technologies", "Technologies"],
  ["has_requirements", "Requirements"],
  ["has_images", "Images"],
  ["has_demo_link", "Demo link"],
];

const EXCLUSION_REASON_LABELS: Record<string, string> = {
  fork_repository: "Fork repository",
  archived_repository: "Arşivlenmiş repository",
};

export function RepositoryAnalysisSection({ repositories, failures, excluded }: RepositoryAnalysisSectionProps) {
  const hasAnyRepositoryState = repositories.length > 0 || failures.length > 0 || excluded.length > 0;

  return (
    <section aria-labelledby="repository-analysis-heading" className="space-y-5">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.16em] text-emerald-600">Repository Analysis</p>
        <h3 id="repository-analysis-heading" className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">Repository kanıtları</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">Her repository için backend analizinin sunduğu deterministic evidence sonuçları.</p>
      </div>

      {repositories.length > 0 ? (
        <div className="space-y-4">{repositories.map((repository) => <RepositoryCard key={repository.repository.html_url} result={repository} />)}</div>
      ) : <EmptyRepositoryState message="Başarılı repository analizi bulunmuyor." />}

      {failures.length > 0 && <FailureSection failures={failures} />}
      {excluded.length > 0 && <ExcludedSection repositories={excluded} />}
      {!hasAnyRepositoryState && <p className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-600">Bu analizde repository sonucu bulunmuyor.</p>}
    </section>
  );
}

function RepositoryCard({ result }: { result: PortfolioRepositoryResult }) {
  const { repository, analysis, score } = result;
  const technologies = analysis.technologies.technologies;
  const categories = analysis.classification.categories;

  return (
    <details className="group rounded-2xl border border-slate-200 bg-white shadow-sm">
      <summary className="flex cursor-pointer list-none items-start gap-3 rounded-2xl p-5 outline-none transition focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 sm:items-center sm:p-6">
        <span aria-hidden="true" className="mt-1 shrink-0 text-xl leading-none text-slate-500 transition-transform group-open:rotate-90">›</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="max-w-full break-words text-lg font-semibold text-slate-950">{repository.name}</span>
            {score.is_partial && <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">Kısmi evidence</span>}
          </div>
          <p className="mt-2 break-words text-sm text-slate-600">{analysis.classification.primary_category}</p>
        </div>
        <div className="w-full shrink-0 sm:w-auto sm:text-right">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">Repository Evidence Score</p>
          <p className="mt-1 text-2xl font-semibold text-slate-950">{score.overall_score} / 100</p>
        </div>
      </summary>
      <div className="border-t border-slate-100 px-5 pb-6 pt-5 sm:px-6">
        <a href={repository.html_url} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center rounded-lg text-sm font-medium text-slate-700 underline decoration-slate-300 underline-offset-4 hover:text-slate-950 hover:decoration-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-950 focus:ring-offset-2">Repository sayfasını aç</a>
        {score.is_partial && <p className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">Repository tree kısmi olduğu için structure-based evidence eksik olabilir. Bu durum analiz hatası değildir.</p>}
        {score.limitations.length > 0 && <ul className="mb-5 space-y-2 text-sm text-slate-600">{score.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>}

        <div className="grid gap-4 md:grid-cols-3">{score.dimensions.map((dimension) => <ScoreDimension key={dimension.key} dimension={dimension} />)}</div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <EvidenceList title="README signals" items={README_LABELS.filter(([key]) => analysis.readme[key]).map(([, label]) => label)} emptyMessage="Tespit edilen README sinyali yok." />
          <EvidenceList title="Repository structure" items={STRUCTURE_LABELS.filter(([key]) => analysis.structure[key]).map(([, label]) => label)} emptyMessage="Tespit edilen structure sinyali yok." />
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <ChipList title="Detected Technologies" items={technologies.map((technology) => technology.name)} emptyMessage="Bu repository için teknoloji sinyali bulunmuyor." />
          <ChipList title="Project Categories" items={categories.map((category) => category.category)} emptyMessage="Bu repository için kategori sinyali bulunmuyor." />
        </div>
        <div className="mt-6"><RuleBreakdown dimensions={score.dimensions} /></div>
      </div>
    </details>
  );
}

function ScoreDimension({ dimension }: { dimension: ScoreDimensionResult }) {
  const progress = Number.isFinite(dimension.score) ? Math.min(100, Math.max(0, dimension.score)) : 0;
  return <article className="min-w-0 rounded-xl bg-slate-50 p-4"><div className="flex flex-wrap items-baseline justify-between gap-2"><h4 className="min-w-0 font-medium text-slate-950">{dimension.label}</h4><span className="shrink-0 text-sm font-semibold text-slate-700">{dimension.points_earned} / {dimension.points_possible}</span></div><div role="progressbar" aria-label={`${dimension.label} skoru`} aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-slate-700" style={{ width: `${progress}%` }} /></div></article>;
}

function RuleBreakdown({ dimensions }: { dimensions: ScoreDimensionResult[] }) {
  return <section aria-labelledby="repository-rules-heading"><h4 id="repository-rules-heading" className="text-sm font-semibold text-slate-950">Evidence breakdown</h4><div className="mt-3 space-y-4">{dimensions.map((dimension) => <div key={dimension.key}><h5 className="text-sm font-medium text-slate-700">{dimension.label}</h5><ul className="mt-2 grid gap-2 sm:grid-cols-2">{dimension.rules.map((rule) => <li key={rule.key} className="rounded-lg border border-slate-200 p-3 text-sm"><div className="flex min-w-0 items-start gap-2"><span aria-hidden="true" className={rule.passed ? "text-emerald-700" : "text-slate-500"}>{rule.passed ? "✓" : "—"}</span><span className="min-w-0 break-words font-medium text-slate-800">{rule.label}</span><span className="ml-auto shrink-0 whitespace-nowrap text-xs text-slate-500">{rule.points_earned} / {rule.points_possible}</span></div><p className="mt-1 break-words pl-5 text-xs leading-5 text-slate-500">{rule.evidence}</p></li>)}</ul></div>)}</div></section>;
}

function EvidenceList({ title, items, emptyMessage }: { title: string; items: string[]; emptyMessage: string }) {
  return <section aria-labelledby={`${title}-heading`}><h4 id={`${title}-heading`} className="text-sm font-semibold text-slate-950">{title}</h4>{items.length > 0 ? <ul className="mt-3 flex flex-wrap gap-2">{items.map((item) => <li key={item} className="rounded-full bg-slate-100 px-3 py-1.5 text-sm text-slate-700">{item}</li>)}</ul> : <p className="mt-3 text-sm text-slate-500">{emptyMessage}</p>}</section>;
}

function ChipList({ title, items, emptyMessage }: { title: string; items: string[]; emptyMessage: string }) {
  return <EvidenceList title={title} items={items} emptyMessage={emptyMessage} />;
}

function FailureSection({ failures }: { failures: PortfolioRepositoryFailure[] }) {
  return <section aria-labelledby="repository-failures-heading" className="rounded-2xl border border-amber-200 bg-amber-50 p-5 sm:p-6"><h4 id="repository-failures-heading" className="text-lg font-semibold text-amber-950">Repository Analysis Issues</h4><p className="mt-2 text-sm text-amber-900">Bu repository’ler için analiz verileri tamamlanamadı.</p><ul className="mt-4 space-y-3">{failures.map((failure) => <li key={`${failure.repository.html_url}-${failure.code}`} className="rounded-xl border border-amber-200 bg-white/70 p-4"><p className="break-words font-medium text-slate-950">{failure.repository.name}</p><p className="mt-1 text-sm leading-6 text-slate-700">{failure.message}</p></li>)}</ul></section>;
}

function ExcludedSection({ repositories }: { repositories: ExcludedPortfolioRepository[] }) {
  return <section aria-labelledby="excluded-repositories-heading" className="rounded-2xl border border-slate-200 bg-slate-50 p-5 sm:p-6"><h4 id="excluded-repositories-heading" className="text-lg font-semibold text-slate-950">Excluded Repositories</h4><p className="mt-2 text-sm text-slate-600">Bu repository’ler seçim politikası nedeniyle analiz kapsamı dışındadır.</p><ul className="mt-4 space-y-2">{repositories.map((item) => <li key={item.repository.html_url} className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg bg-white p-3 text-sm"><span className="break-words font-medium text-slate-800">{item.repository.name}</span><span className="break-words text-slate-500">{item.reasons.map((reason) => EXCLUSION_REASON_LABELS[reason] || "Seçim politikası").join(" · ")}</span></li>)}</ul></section>;
}

function EmptyRepositoryState({ message }: { message: string }) {
  return <p className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-600">{message}</p>;
}
